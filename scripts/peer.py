#!/usr/bin/env python3
"""同类ETF自动对比模块。"""

# 常见ETF同类映射
ETF_PEER_MAP = {
    "510300": ["159919", "510330", "510310"],  # 沪深300
    "510500": ["159922", "512500"],             # 中证500
    "159915": ["159952", "159958"],             # 创业板
    "588000": ["588080", "588050"],             # 科创50
    "512480": ["159813", "159995"],             # 半导体
    "159732": ["561600", "159787"],             # 消费电子
    "510050": ["510710", "510880"],             # 上证50
    "510880": ["159965", "510050"],             # 红利
    "159949": ["159967", "159966"],             # 创业板50
    "512100": ["159845", "159990"],             # 中证1000
    "159845": ["512100", "159990"],             # 中证1000
}


def get_peers(fund_code):
    """返回同类ETF代码列表。未匹配返回空列表。"""
    return ETF_PEER_MAP.get(fund_code, [])


def compare_peers(fund_code, peer_codes):
    """
    同类ETF对比。

    通过 tencent_quote 批量获取行情，对比规模/换手率/成交额。

    参数：
        fund_code — 本基金代码
        peer_codes — 同类代码列表

    返回：
    {
        "comparison_table": [
            {"code": ..., "name": ..., "mcap_yi": ..., "turnover": ..., "amount_wan": ..., "pe_rank": "前1/3"/"中"/"后1/3"},
            ...
        ],
        "peer_avg_scale": float,
        "fund_rank_position": "前1/3"/"中"/"后1/3",
        "best_peer": {"code": ..., "name": ..., "mcap_yi": ...},
    }
    """
    from .fund_data import tencent_quote

    all_codes = [fund_code] + peer_codes
    quotes = tencent_quote(all_codes)

    if quotes.get("error"):
        return {"error": True}

    # 构建对比表
    table = []
    for code in all_codes:
        if code not in quotes:
            continue
        q = quotes[code]
        table.append({
            "code": code,
            "name": q.get("name", ""),
            "mcap_yi": q.get("mcap_yi", 0),
            "turnover": q.get("turnover_pct", 0),
            "amount_wan": q.get("amount_wan", 0),
        })

    if not table:
        return {"error": True, "comparison_table": []}

    # 按规模排序确定排位
    table_sorted = sorted(table, key=lambda x: x["mcap_yi"], reverse=True)
    n = len(table_sorted)
    peer_avg_scale = round(sum(r["mcap_yi"] for r in table_sorted) / n, 2)

    fund_rank = 0
    best_peer = None
    for i, r in enumerate(table_sorted):
        if r["code"] == fund_code:
            fund_rank = i + 1
        if r["code"] != fund_code and (best_peer is None or r["mcap_yi"] > best_peer["mcap_yi"]):
            best_peer = {"code": r["code"], "name": r["name"], "mcap_yi": r["mcap_yi"]}

    # 排名位置
    if n <= 3:
        if fund_rank <= 1:
            fund_rank_position = "前1/3"
        elif fund_rank <= 2:
            fund_rank_position = "中"
        else:
            fund_rank_position = "后1/3"
    else:
        third = n / 3
        if fund_rank <= third:
            fund_rank_position = "前1/3"
        elif fund_rank <= third * 2:
            fund_rank_position = "中"
        else:
            fund_rank_position = "后1/3"

    # 添加排名标记到对比表
    for i, r in enumerate(table_sorted):
        if n <= 3:
            if i == 0:
                r["pe_rank"] = "前1/3"
            elif i == 1:
                r["pe_rank"] = "中"
            else:
                r["pe_rank"] = "后1/3"
        else:
            third = n / 3
            if i < third:
                r["pe_rank"] = "前1/3"
            elif i < third * 2:
                r["pe_rank"] = "中"
            else:
                r["pe_rank"] = "后1/3"

    return {
        "comparison_table": table_sorted,
        "peer_avg_scale": peer_avg_scale,
        "fund_rank_position": fund_rank_position,
        "best_peer": best_peer if best_peer else {"code": fund_code, "name": "", "mcap_yi": 0},
    }
