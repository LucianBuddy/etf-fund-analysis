#!/usr/bin/env python3
"""ETF/基金持仓风险分析。"""

INDUSTRY_KEYWORDS = {
    "消费电子": ["电子", "科技", "信息", "通信", "半导体", "芯片", "消费电子"],
    "新能源": ["新能源", "光伏", "锂电", "电池", "电车", "汽车"],
    "医药": ["医药", "医疗", "生物", "药", "健康"],
    "金融": ["银行", "保险", "证券", "金融"],
    "消费": ["消费", "白酒", "食品", "饮料", "家电", "零售"],
    "制造": ["制造", "机械", "军工", "航空", "电力设备"],
    "周期": ["有色", "钢铁", "煤炭", "化工", "石油", "建材"],
}


def _guess_industry(name):
    """根据股票名猜测行业。返回行业名或'其他'。"""
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return industry
    return "其他"


def holdings_risk_analysis(holdings):
    """
    对基金重仓股做风险分析。

    参数 holdings: [{"code":"002475","name":"立讯精密","pct":8.5,"pe":31,"industry":"消费电子"}, ...]
    最少每个元素应有 name 和 pct 字段。industry/market/pe 可选。

    返回:
    {
        "top1_pct": float,             # 最大单只占比
        "top3_pct": float,             # TOP3合计占比
        "top3_names": [str],           # TOP3股票名
        "industry_top3_pct": float,    # TOP3行业占比
        "industry_dist": {str: float}, # 行业分布 {行业: 占比}
        "concentration_risk": str,     # "高度集中"/"集中"/"分散"
        "has_high_pe": bool,           # 是否有PE>100的持仓
        "has_negative_pe": bool,       # 是否有亏损股(PE<0)
        "style": str,                  # 风格: 价值/均衡/成长
        "detail": str,
    }

    规则:
    top1 > 20% → "高度集中"
    top1 > 15% 或 top3 > 40% → "集中"
    其他 → "分散"
    industry_top3 > 60% → 行业集中标记
    has_high_pe / has_negative_pe → 风险标记
    """
    if not holdings:
        return {
            "top1_pct": 0,
            "top3_pct": 0,
            "top3_names": [],
            "industry_top3_pct": 0,
            "industry_dist": {},
            "concentration_risk": "数据不足",
            "has_high_pe": False,
            "has_negative_pe": False,
            "style": "数据不足",
            "detail": "无持仓数据",
        }

    # 按占比排序
    sorted_h = sorted(holdings, key=lambda h: h.get("pct", 0), reverse=True)
    top3 = sorted_h[:3]
    top3_names = [h.get("name", "") for h in top3]
    top1_pct = round(top3[0].get("pct", 0), 2) if top3 else 0
    top3_pct = round(sum(h.get("pct", 0) for h in top3), 2)

    # 集中度判断
    if top1_pct > 20:
        concentration_risk = "高度集中"
    elif top1_pct > 15 or top3_pct > 40:
        concentration_risk = "集中"
    else:
        concentration_risk = "分散"

    # 行业分布
    industry_pcts = {}
    for h in sorted_h:
        ind = h.get("industry") or _guess_industry(h.get("name", ""))
        pct = h.get("pct", 0)
        industry_pcts[ind] = industry_pcts.get(ind, 0) + pct
    for ind in industry_pcts:
        industry_pcts[ind] = round(industry_pcts[ind], 2)

    # TOP3行业占比
    sorted_inds = sorted(industry_pcts.items(), key=lambda x: x[1], reverse=True)
    industry_top3_pct = round(sum(v for _, v in sorted_inds[:3]), 2)

    # PE检测
    has_high_pe = any(h.get("pe") and h["pe"] > 100 for h in holdings)
    has_negative_pe = any(h.get("pe") and h["pe"] < 0 for h in holdings)

    # 风格判断
    pe_list = [h.get("pe") for h in holdings if h.get("pe")]
    from .fund_data import classify_style
    style = classify_style(pe_list)

    # detail 文本
    detail_parts = []
    detail_parts.append(f"前3集中度{top3_pct}%（{', '.join(top3_names)}）")
    detail_parts.append(f"行业集中度：TOP3行业{industry_top3_pct}%")
    if concentration_risk == "高度集中":
        detail_parts.append(f"⚠ 最大重仓股{top1_pct}%（>20%）：高度集中风险")
    elif concentration_risk == "集中":
        detail_parts.append(f"持仓集中【TOP1={top1_pct}%, TOP3={top3_pct}%】")
    else:
        detail_parts.append("持仓分散")
    if has_high_pe:
        detail_parts.append("⚠ 存在高PE（>100）持仓")
    if has_negative_pe:
        detail_parts.append("⚠ 存在亏损股（PE<0）")
    detail_parts.append(f"组合风格：{style}")

    return {
        "top1_pct": top1_pct,
        "top3_pct": top3_pct,
        "top3_names": top3_names,
        "industry_top3_pct": industry_top3_pct,
        "industry_dist": industry_pcts,
        "concentration_risk": concentration_risk,
        "has_high_pe": has_high_pe,
        "has_negative_pe": has_negative_pe,
        "style": style,
        "detail": " | ".join(detail_parts),
    }
