#!/usr/bin/env python3
"""ETF追踪记录与预警模块。"""

import json
import os
from datetime import datetime, timedelta

TRACKER_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fund_tracker.json"
)


def track_fund(code, name, size_yi, prem_pct, track_err=None, style=None):
    """
    记录一次基金分析快照。

    每次分析ETF时调用，累积规模/折溢价/跟踪误差的历史记录。
    用于趋势判断（规模连续下降预警）。

    记录格式：
    {"code":"510300","name":"沪深300ETF","date":"2026-06-26",
     "size_yi":350, "prem_pct":0.15, "track_err":0.12}
    """
    records = _load()
    records.append({
        "code": code,
        "name": name,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "size_yi": size_yi,
        "prem_pct": prem_pct,
        "track_err": track_err,
        "style": style or "",
    })
    _save(records)


def check_alerts(code, lookback_days=90):
    """
    检查需要预警的风险。

    检查项：
    1. 规模连续3次下降且累计>20% → "规模萎缩预警"
    2. 最近一次折溢价>2% → "折溢价异常预警"
    3. 跟踪误差恶化 → "跟踪误差预警"

    返回 [{"type": str, "severity": "高/中", "detail": str}, ...]
    """
    records = _load()
    code_records = [r for r in records if r["code"] == code]

    if not code_records:
        return []

    alerts = []
    cutoff = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    recent = [r for r in code_records if r["date"] >= cutoff]

    # 1. 规模萎缩预警
    size_records = [r for r in recent if r.get("size_yi") is not None]
    if len(size_records) >= 3:
        size_records = sorted(size_records, key=lambda r: r["date"])
        # 检查是否连续下降
        declines = 0
        for i in range(len(size_records) - 1):
            if size_records[i + 1]["size_yi"] < size_records[i]["size_yi"]:
                declines += 1
        if declines >= 2:
            # 检查累计降幅
            first_size = size_records[0]["size_yi"]
            last_size = size_records[-1]["size_yi"]
            if first_size > 0:
                drop_pct = (first_size - last_size) / first_size * 100
                if drop_pct > 20:
                    alerts.append({
                        "type": "规模萎缩预警",
                        "severity": "高",
                        "detail": f"规模从{first_size}亿降至{last_size}亿，累计下降{drop_pct:.1f}%（>20%），警惕清盘风险",
                    })
                elif drop_pct > 10:
                    alerts.append({
                        "type": "规模下降",
                        "severity": "中",
                        "detail": f"规模从{first_size}亿降至{last_size}亿，累计下降{drop_pct:.1f}%",
                    })

    # 2. 折溢价异常预警
    prem_records = [r for r in recent if r.get("prem_pct") is not None]
    if prem_records:
        last_prem = prem_records[-1]["prem_pct"]
        last_prem_abs = abs(last_prem)
        if last_prem_abs > 2:
            direction = "溢价" if last_prem > 0 else "折价"
            alerts.append({
                "type": "折溢价异常预警",
                "severity": "高" if last_prem_abs > 3 else "中",
                "detail": f"最新{last_prem:.2f}%（{direction}异常），正常范围应在±1%以内",
            })

    # 3. 跟踪误差恶化检查
    err_records = [r for r in recent if r.get("track_err") is not None]
    if len(err_records) >= 2:
        err_records = sorted(err_records, key=lambda r: r["date"])
        last_err = err_records[-1]["track_err"]
        if last_err and last_err > 0.5:
            # 检查趋势
            first_err = err_records[0]["track_err"]
            if first_err and last_err > first_err:
                alerts.append({
                    "type": "跟踪误差预警",
                    "severity": "中",
                    "detail": f"跟踪误差从{first_err}%上升至{last_err}%（>0.5%），跟踪能力恶化",
                })
            else:
                alerts.append({
                    "type": "跟踪误差预警",
                    "severity": "中",
                    "detail": f"最新跟踪误差{last_err}%（>0.5%），需警惕跟踪偏离",
                })

    return alerts


def get_track_history(code):
    """获取某ETF的完整追踪历史。"""
    records = _load()
    return [r for r in records if r["code"] == code]


def check_style_drift(code, current_style=None):
    """
    检测主动基金的持仓风格是否发生变化。

    通过历史追踪记录中 style 字段的序列判断。

    参数：
        code — 基金代码
        current_style — 当前判断的风格（可选，"价值"/"均衡"/"成长"）

    返回：
    {
        "drift_detected": bool,        # 是否发生漂移
        "style_history": [str],        # 历史风格序列
        "current_style": str,          # 当前风格（或最近一次记录的风格）
        "first_style": str,            # 首次记录的风格
        "changed": bool,               # 风格是否发生过变化
        "detail": str,
    }

    规则：
    从 fund_tracker.json 中提取该 code 的所有记录，
    如果存在多次不同的 style 值，则标记 drift_detected=True。
    """
    records = _load()
    fund_records = [r for r in records if r.get("code") == code]

    if not fund_records:
        first_style = current_style or "未知"
        return {"drift_detected": False, "style_history": [first_style],
                "current_style": first_style, "first_style": first_style,
                "changed": False, "detail": "无历史记录"}

    # 提取所有 style
    styles = []
    for r in fund_records:
        s = r.get("style")
        if s and s not in ("未知", ""):
            styles.append(s)

    if current_style:
        styles.append(current_style)

    if not styles:
        return {"drift_detected": False, "style_history": [],
                "current_style": "未知", "first_style": "未知",
                "changed": False, "detail": "无风格数据"}

    unique_styles = list(dict.fromkeys(styles))  # 保持顺序去重
    drifted = len(unique_styles) > 1

    detail = f"风格历史: {'→'.join(unique_styles)}"
    if drifted:
        detail += f"，检测到风格漂移({unique_styles[0]}→{unique_styles[-1]})"
    else:
        detail += "，风格稳定"

    return {
        "drift_detected": drifted,
        "style_history": unique_styles,
        "current_style": styles[-1],
        "first_style": styles[0],
        "changed": drifted,
        "detail": detail,
    }


def _load():
    try:
        if os.path.exists(TRACKER_FILE):
            with open(TRACKER_FILE) as f:
                return json.load(f)
    except:
        pass
    return []


def _save(records):
    try:
        os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)
        with open(TRACKER_FILE, "w") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except:
        pass
