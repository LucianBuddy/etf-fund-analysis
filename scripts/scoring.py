#!/usr/bin/env python3
"""
ETF质量评分系统。
替代 LLM 手动累加5项指标的过程。
"""


def score_fee(total_fee):
    """费率评分。fee% <0.2→1, <0.5→0, >=0.5→-1"""
    if total_fee < 0.2:
        return 1, "低"
    elif total_fee < 0.5:
        return 0, "中"
    else:
        return -1, "高"


def score_tracking_error(error):
    """跟踪误差评分。error% <0.2→1, <0.5→0, >=0.5→-1"""
    if error < 0.2:
        return 1, "小"
    elif error < 0.5:
        return 0, "可接受"
    else:
        return -1, "差"


def score_scale(size_yi):
    """规模评分。>50→1, >10→0, <=10→-1"""
    if size_yi > 50:
        return 1, "大"
    elif size_yi > 10:
        return 0, "中"
    else:
        return -1, "小"


def score_premium(prem_pct):
    """折溢价评分。|%|<1→1, 其他→-1"""
    if abs(prem_pct) < 1:
        return 1, "正常"
    else:
        return -1, "异常"


def score_liquidity(turnover_pct, amount_wan):
    """流动性评分。换手率>1%或成交额>5000万→1, 其他→0"""
    if turnover_pct > 1 or amount_wan > 5000:
        return 1, "好"
    return 0, "一般"


def score_etf_quality(fund_data):
    """
    ETF 5项质量评分。

    参数 fund_data dict:
        {total_fee, track_err, size_yi, prem_pct, turnover_pct, amount_wan, ...}

    返回:
    {
        "total_score": int,        # -5~5
        "max_score": 5,
        "details": {
            "费率": {"score": 1, "label": "低", "value": 0.15},
            "跟踪误差": {"score": 1, "label": "小", "value": 0.1},
            ...
        },
        "verdict": "推荐"/"可考虑"/"不推荐",
        "n_available": int,        # 有效评分项数
    }

    推荐规则：
    >=4分 → "推荐"
    3分 → "可考虑"
    <=2分 → "不推荐"
    """
    fee = fund_data.get("total_fee", 999)
    err = fund_data.get("track_err", 999)
    size_yi = fund_data.get("size_yi", 0)
    prem = fund_data.get("prem_pct", 0)
    turnover = fund_data.get("turnover_pct", 0)
    amount = fund_data.get("amount_wan", 0)

    items = [
        ("费率", score_fee(fee)),
        ("跟踪误差", score_tracking_error(err)),
        ("规模", score_scale(size_yi)),
        ("折溢价", score_premium(prem)),
        ("流动性", score_liquidity(turnover, amount)),
    ]

    value_map = {
        "费率": fee,
        "跟踪误差": err,
        "规模": size_yi,
        "折溢价": prem,
        "流动性": turnover,
    }

    details = {}
    total = 0
    n_valid = 0

    for name, (sc, label) in items:
        raw_val = value_map[name] if name in value_map else 0
        details[name] = {"score": sc, "label": label, "value": raw_val}
        total += sc
        n_valid += 1

    if total >= 4:
        verdict = "推荐"
    elif total >= 3:
        verdict = "可考虑"
    else:
        verdict = "不推荐"

    return {
        "total_score": total,
        "max_score": 5,
        "details": details,
        "verdict": verdict,
        "n_available": n_valid,
    }
