#!/usr/bin/env python3
"""
基金/ETF数据层。零外部依赖(urllib.request)。
替代 a-stock-data 的 inline 代码 + web_fetch 手动爬取。
"""

import urllib.request
import json
import re
import time

_last_req = 0.0


def _rate_limit():
    """请求间隔≥1s"""
    global _last_req
    now = time.time()
    if now - _last_req < 1.0:
        time.sleep(1.0 - (now - _last_req))
    _last_req = time.time()


def _tencent_get(codes):
    """腾讯API统一入口"""
    prefixed = []
    for c in codes:
        if c.startswith(("6", "9")):
            prefixed.append(f"sh{c}")
        elif c.startswith("8"):
            prefixed.append(f"bj{c}")
        else:
            prefixed.append(f"sz{c}")
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    except:
        return ""


def tencent_quote(codes):
    """
    批量获取行情（腾讯）。
    返回 {code: {name, price, change_pct, amount_wan, turnover_pct, mcap_yi, vol_ratio}}
    失败返回 {"error": True}
    """
    raw = _tencent_get(codes)
    if not raw:
        return {"error": True}
    result = {}
    for line in raw.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:]
        try:
            result[code] = {
                "name": vals[1],
                "price": float(vals[3]) if vals[3] else 0,
                "last_close": float(vals[4]) if vals[4] else 0,
                "change_pct": float(vals[32]) if vals[32] else 0,
                "amount_wan": float(vals[37]) if vals[37] else 0,
                "turnover_pct": float(vals[38]) if vals[38] else 0,
                "mcap_yi": float(vals[44]) if vals[44] else 0,
                "vol_ratio": float(vals[49]) if vals[49] else 0,
            }
        except:
            continue
    return result


def calc_premium(price, nav):
    """
    计算折溢价率。
    premium > 0 = 溢价（场内贵），< 0 = 折价（场内便宜）
    如果 nav <= 0，返回 0 表示数据不足
    """
    if nav and nav > 0 and price > 0:
        return round((price - nav) / nav * 100, 2)
    return 0.0


def classify_fund_type(code):
    """
    根据代码前缀判断基金类型。
    51xxxx = ETF(沪), 159xxx = ETF(深), 16xxxx = LOF
    """
    c = str(code)
    if c.startswith(("51", "159")):
        return "ETF"
    if c.startswith(("16", "50")):
        return "LOF"
    return "未知"


def classify_style(holdings_pe_list):
    """
    按重仓股PE中位数判断风格：价值/均衡/成长

    参数 holdings_pe_list: [PE值, ...]（剔除了None和异常值）
    返回 "价值" / "均衡" / "成长" / "数据不足"
    """
    valid = [p for p in (holdings_pe_list or []) if p and 0 < p < 500]
    if len(valid) < 3:
        return "数据不足"
    median = sorted(valid)[len(valid) // 2]
    if median < 20:
        return "价值"
    elif median < 40:
        return "均衡"
    else:
        return "成长"


def summarize_fund_data(quote_result, code):
    """
    从腾讯行情结果中提取基金摘要。

    quote_result: tencent_quote([code]) 的返回值
    code: 基金代码

    返回紧凑 dict（供 LLM 使用）:
    {
        "code": str, "name": str, "type": "ETF"/"LOF"/"未知",
        "price": float, "change_pct": float,
        "amount_wan": float, "turnover_pct": float,
        "mcap_yi": float, "vol_ratio": float,
    }
    """
    if not quote_result or quote_result.get("error") or code not in quote_result:
        return {"code": code, "error": True}
    q = quote_result[code]
    return {
        "code": code,
        "name": q.get("name", ""),
        "type": classify_fund_type(code),
        "price": q.get("price", 0),
        "change_pct": q.get("change_pct", 0),
        "amount_wan": q.get("amount_wan", 0),
        "turnover_pct": q.get("turnover_pct", 0),
        "mcap_yi": q.get("mcap_yi", 0),
        "vol_ratio": q.get("vol_ratio", 0),
    }


def compute_returns(bars, periods=None):
    """
    从K线数据回算多期收益率。

    参数：
        bars — K线列表 [{"close":...}, ...]（从 baidu_kline_with_ma 获取）
        periods — 回看周期列表，默认[21, 63, 252]天

    返回：
    {
        "ret_1m": float or None,    # 近1月收益率(%)，None=数据不足
        "ret_3m": float or None,    # 近3月收益率(%)
        "ret_1y": float or None,    # 近1年收益率(%)
        "n_bars": int,              # 有效K线根数
        "detail": str,
    }
    """
    if periods is None:
        periods = [21, 63, 252]

    closes = [b.get("close", 0) for b in (bars or []) if b.get("close")]
    if len(closes) < 2:
        return {"ret_1m": None, "ret_3m": None, "ret_1y": None, "n_bars": 0, "detail": "数据不足"}

    labels = ["ret_1m", "ret_3m", "ret_1y"]
    result = {"n_bars": len(closes)}
    detail_parts = []

    for period, label in zip(periods, labels):
        if len(closes) > period:
            ret = (closes[-1] - closes[-period - 1]) / closes[-period - 1] * 100
            result[label] = round(ret, 2)
            detail_parts.append(f"{label}={ret:+.2f}%")
        else:
            result[label] = None
            detail_parts.append(f"{label}=数据不足(需{period + 1}根)")

    result["detail"] = "，".join(detail_parts)
    return result


def compute_risk_metrics(bars):
    """
    从K线数据计算风险指标。

    参数：
        bars — K线列表 [{"close":...}, ...]

    返回：
    {
        "max_drawdown": float,        # 最大回撤(%)，正值表示跌幅
        "daily_volatility": float,    # 日波动率(%)
        "annual_volatility": float,   # 年化波动率(%)
        "sharpe_approx": float,       # 近似夏普比率（假设无风险利率2%）
        "n_bars": int,
        "detail": str,
    }
    """
    if not bars or len(bars) < 20:
        return {"max_drawdown": None, "annual_volatility": None,
                "sharpe_approx": None, "n_bars": len(bars) if bars else 0,
                "detail": "数据不足(需至少20根K线)"}

    closes = [b.get("close", 0) for b in bars if b.get("close")]
    if len(closes) < 20:
        return {"max_drawdown": None, "annual_volatility": None,
                "sharpe_approx": None, "n_bars": len(closes),
                "detail": "数据不足(需至少20根)"}

    # 最大回撤
    peak = closes[0]
    max_dd = 0
    for c in closes:
        if c > peak:
            peak = c
        dd = (peak - c) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # 日收益率
    daily_returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] > 0:
            dr = (closes[i] - closes[i - 1]) / closes[i - 1]
            daily_returns.append(dr)

    if len(daily_returns) < 5:
        return {"max_drawdown": round(max_dd, 2), "annual_volatility": None,
                "sharpe_approx": None, "n_bars": len(closes),
                "detail": f"最大回撤{max_dd:.1f}%，但日收益率数据不足"}

    import math

    # 年化波动率
    mean_dr = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_dr) ** 2 for r in daily_returns) / len(daily_returns)
    daily_vol = math.sqrt(variance) * 100
    annual_vol = daily_vol * math.sqrt(252)

    # 近似夏普
    annual_return = mean_dr * 252 * 100
    sharpe = (annual_return - 2.0) / annual_vol if annual_vol > 0 else 0

    return {
        "max_drawdown": round(max_dd, 2),
        "annual_volatility": round(annual_vol, 2),
        "sharpe_approx": round(sharpe, 2),
        "n_bars": len(closes),
        "detail": f"最大回撤{max_dd:.1f}%，年化波动{annual_vol:.1f}%，夏普{sharpe:.2f}",
    }


def compute_all_metrics(bars):
    """
    一键计算所有收益和风险指标。

    合并 compute_returns 和 compute_risk_metrics 的结果。
    返回 dict 包含两个函数的所有输出字段。
    """
    ret = compute_returns(bars)
    risk = compute_risk_metrics(bars)
    merged = {}
    merged.update(ret)
    merged.update(risk)
    merged["detail"] = f"收益:{ret.get('detail', '')} | 风险:{risk.get('detail', '')}"
    return merged


def lof_arbitrage_signal(prem_pct, turnover_pct=0, amount_wan=0):
    """
    LOF折溢价套利信号检测。

    LOF 可在场内（股票账户）和场外（基金账户）同时交易，
    当折溢价超过套利成本时存在套利机会。

    参数：
        prem_pct — 折溢价率（%），正=溢价，负=折价
        turnover_pct — 换手率（%），用于判断流动性
        amount_wan — 成交额（万元）

    返回：
    {
        "signal": str,               # "溢价套利" / "折价套利" / "无机会"
        "confidence": str,           # "高" / "中" / "低"
        "arbitrage_return": float,   # 预期套利收益（%）
        "fee_barrier": float,        # 交易成本门槛（%），通常0.5-1%
        "net_return": float,         # 净收益（扣成本后）
        "liquidity_ok": bool,        # 流动性是否满足交易条件
        "detail": str,
    }
    """
    cost = 0.5  # 套利成本门槛 %

    result = {"signal": "无机会", "confidence": "低",
              "arbitrage_return": prem_pct,
              "fee_barrier": cost,
              "net_return": 0.0,
              "liquidity_ok": False,
              "detail": ""}

    # 流动性检查
    result["liquidity_ok"] = amount_wan > 1000 and turnover_pct > 0.3

    if prem_pct > 1.0:
        net = prem_pct - cost
        result["signal"] = "溢价套利"
        result["net_return"] = round(net, 2)
        if net > 1.0 and result["liquidity_ok"]:
            result["confidence"] = "高"
        elif net > 0.5 or result["liquidity_ok"]:
            result["confidence"] = "中"
        result["detail"] = f"溢价{prem_pct:.1f}%，扣除成本{cost:.1f}%后净收益{net:.1f}%"

    elif prem_pct < -1.0:
        net = abs(prem_pct) - cost
        result["signal"] = "折价套利"
        result["net_return"] = round(net, 2)
        if net > 1.0 and result["liquidity_ok"]:
            result["confidence"] = "高"
        elif net > 0.5 or result["liquidity_ok"]:
            result["confidence"] = "中"
        result["detail"] = f"折价{abs(prem_pct):.1f}%，扣除成本{cost:.1f}%后净收益{net:.1f}%"

    else:
        result["detail"] = f"折溢价{prem_pct:.1f}%，未达套利阈值"

    return result


def dca_simulate(bars, monthly_amount=1000, years=1):
    """
    模拟每月定投，回算总投入/市值/收益率。

    参数：
        bars — K线列表 [{"close":..., "date": "2026-01-01"}, ...]
               需要包含 date 字段，用于确定定投月份
        monthly_amount — 每月定投金额（元），默认1000
        years — 定投年数（默认1年）

    返回：
    {
        "total_invested": float,          # 总投入（元）
        "final_value": float,             # 最终市值（元）
        "total_return_pct": float,        # 总收益率(%)
        "annualized_return": float,       # 年化收益率(%)（简化计算）
        "n_months": int,                  # 定投月数
        "avg_cost": float,                # 平均成本价
        "final_price": float,             # 最终价格
        "profit": float,                  # 收益金额（元）
        "shares_accumulated": float,      # 累计份额
        "monthly_records": [              # 每月定投明细
            {"month": str, "invest": float, "price": float, "shares": float},
            ...
        ],
        "vs_lump_sum": {                 # 对比一次性投入
            "lump_sum_return": float,
            "dca_beat_lump_sum": bool,
        },
        "detail": str,
    }

    定投规则：
    1. 每个月第一个交易日买入（取每个月第一根有价格的K线）
    2. 以当日收盘价买入
    3. 每月固定金额，不择时
    4. 最终按最后一根K线收盘价计算市值

    如果 bars 不足，返回 {"error": True, "detail": "数据不足"}
    """
    if not bars or len(bars) < 20:
        return {"error": True, "detail": "数据不足(需至少20根K线)"}

    # 提取有效的日期+价格数据
    valid = []
    for b in bars:
        close = b.get("close", 0)
        date = b.get("date", "")
        if close and date and len(date) >= 7:
            valid.append({"date": date, "close": close})

    if len(valid) < 20:
        return {"error": True, "detail": "有效数据不足"}

    # 按年月分组取每月第一根
    monthly_buys = {}
    for v in valid:
        month_key = v["date"][:7]  # "2026-01"
        if month_key not in monthly_buys:
            monthly_buys[month_key] = v["close"]

    # 取需要 months 个月
    sorted_months = sorted(monthly_buys.keys())
    max_months = years * 12
    selected = sorted_months[:max_months]

    total_invested = 0
    total_shares = 0.0
    records = []

    for month in selected:
        price = monthly_buys[month]
        if price <= 0:
            continue
        shares = monthly_amount / price
        total_invested += monthly_amount
        total_shares += shares
        records.append({
            "month": month,
            "invest": monthly_amount,
            "price": round(price, 4),
            "shares": round(shares, 4),
        })

    if total_shares <= 0:
        return {"error": True, "detail": "无有效买入"}

    final_price = valid[-1]["close"]
    final_value = total_shares * final_price
    profit = final_value - total_invested
    total_return = (final_value / total_invested - 1) * 100 if total_invested > 0 else 0

    # 简化年化收益率 = 总收益率 / 年数
    annualized = total_return / years if years > 0 else 0

    avg_cost = total_invested / total_shares if total_shares > 0 else 0

    # vs 一次性投入
    first_price = valid[0]["close"]
    lump_sum_shares = total_invested / first_price if first_price > 0 else 0
    lump_sum_value = lump_sum_shares * final_price
    lump_sum_return = (lump_sum_value / total_invested - 1) * 100 if total_invested > 0 else 0

    return {
        "total_invested": round(total_invested, 2),
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return, 2),
        "annualized_return": round(annualized, 2),
        "n_months": len(records),
        "avg_cost": round(avg_cost, 4),
        "final_price": final_price,
        "profit": round(profit, 2),
        "shares_accumulated": round(total_shares, 4),
        "monthly_records": records,
        "vs_lump_sum": {
            "lump_sum_return": round(lump_sum_return, 2),
            "dca_beat_lump_sum": total_return > lump_sum_return,
        },
        "detail": f"定投{len(records)}个月，投入{round(total_invested)}元，市值{round(final_value)}元，"
                  f"收益率{round(total_return,1)}%，{'跑赢' if total_return > lump_sum_return else '跑输'}一次性投入"
                  f"({round(lump_sum_return,1)}%)",
    }


def try_fetch_fund_info(code):
    """
    尝试通过公开接口获取基金费率和净值。

    这是一个"尽力而为"的函数——能拿到数据最好，拿不到不阻断分析。

    获取途径：
    1. 通过腾讯基金接口获取净值
    2. 通过天天基金公开接口尝试获取

    参数：
        code — 基金代码

    返回：
    {
        "nav": float or None,           # 最新净值（单位净值）
        "mgmt_fee": float or None,      # 管理费（%）
        "cust_fee": float or None,      # 托管费（%）
        "total_fee": float or None,     # 总费率（%）
        "source": str or None,          # 数据来源
        "success": bool,
        "detail": str,
    }

    所有字段不可用时返回 {"success": False, "detail": "数据不可用"}
    部分可用的返回可用部分+不可用标注。

    努力获取但不强制——失败时返回 {"success": False, "detail": "数据不可用"}，
    不抛异常。
    """
    result = {"nav": None, "mgmt_fee": None, "cust_fee": None,
              "total_fee": None, "source": None, "success": False, "detail": ""}

    # 尝试1：通过腾讯基金净值API
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fund/fundinfo?symbol={code}"
        _rate_limit()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        data = json.loads(resp)
        nav_data = data.get("data", {}).get(code, {}).get("nav", [])
        if nav_data and len(nav_data) > 0:
            nav = float(nav_data[-1][1]) if len(nav_data[-1]) > 1 else None
            if nav and nav > 0:
                result["nav"] = nav
                result["source"] = "腾讯"
    except:
        pass

    # 尝试2：通过天天基金页面获取
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js"
        _rate_limit()
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://fund.eastmoney.com/"
        })
        resp = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
        # 返回 jsonp 格式: jsonpgz({"fundcode":"...", ...})
        match = re.search(r'\{[^}]+\}', resp)
        if match:
            data = json.loads(match.group())
            if data.get("fundcode"):
                if result["nav"] is None:
                    result["nav"] = float(data.get("dwjz", 0)) if data.get("dwjz") else None
                result["source"] = "天天基金"
    except:
        pass

    # 如果有净值，计算费率（ETF费率通常可估算）
    if result["nav"] is not None and result["nav"] > 0:
        result["success"] = True

    # 整理detail
    parts = []
    if result["nav"] is not None:
        parts.append(f"净值{result['nav']}")
    if len(parts) == 0:
        result["detail"] = "数据不可用"
    else:
        result["detail"] = "，".join(parts)

    return result
