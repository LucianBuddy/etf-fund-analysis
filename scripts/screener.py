#!/usr/bin/env python3
"""
ETF批量筛选模块。
一次分析多只ETF，按质量评分排序。
"""

from .fund_data import tencent_quote, calc_premium, summarize_fund_data
from .scoring import score_etf_quality

# 预设ETF分类
ETF_CATEGORIES = {
    "宽基": ["510300", "510500", "159915", "588000", "510050", "159845"],
    "行业半导体": ["512480", "159813", "159995"],
    "行业消费电子": ["159732", "561600", "159787"],
    "行业医药": ["512010", "159865", "159929"],
    "行业新能源": ["515030", "159930", "516160"],
    "主题红利": ["510880", "159965", "515080"],
    "主题证券": ["512880", "159841", "512000"],
    "主题军工": ["512660", "159931", "512710"],
}


def screen_etfs(code_list, use_cache=True):
    """
    批量筛选ETF，按质量评分排序。

    对每只ETF：
    1. tencent_quote 获取实时行情
    2. 提取价格/规模/换手率/成交额
    3. score_etf_quality 计算质量评分

    参数：
        code_list — ETF代码列表，如 ["510300", "159915", "510500"]
        use_cache — 是否使用缓存（默认True）

    返回：
    {
        "total": int,
        "success": int,
        "failed": int,
        "errors": [str],
        "ranked": [
            {
                "rank": int,
                "code": str,
                "name": str,
                "total_score": int,       # 质量评分(0~5)
                "verdict": str,           # "推荐"/"可考虑"/"不推荐"
                "price": float,
                "change_pct": float,
                "mcap_yi": float,
                "prem_pct": float,
                "turnover_pct": float,
                "details": dict,          # 各维度评分详情
            },
            ...
        ],
        "best": {"code": str, "name": str, "score": int},
        "summary": str,
    }

    排序：按 total_score 降序，同分按 mcap_yi 降序。
    """
    results = {"total": len(code_list), "success": 0, "failed": 0,
               "errors": [], "ranked": [], "best": None, "summary": ""}

    for code in code_list:
        try:
            quote = tencent_quote([code])
            if quote.get("error") or code not in quote:
                results["failed"] += 1
                results["errors"].append(f"{code}: 行情不可用")
                continue

            q = quote[code]
            fund_data = {
                "total_fee": 0.0,     # 费率数据暂缺，用0表示未知
                "track_err": 0.0,
                "size_yi": q.get("mcap_yi", 0) or 0,
                "prem_pct": 0.0,      # 折溢价暂缺净值数据
                "turnover_pct": q.get("turnover_pct", 0) or 0,
                "amount_wan": q.get("amount_wan", 0) or 0,
            }

            quality = score_etf_quality(fund_data)

            entry = {
                "rank": 0,
                "code": code,
                "name": q.get("name", ""),
                "total_score": quality.get("total_score", 0),
                "verdict": quality.get("verdict", "数据不足"),
                "price": q.get("price", 0),
                "change_pct": q.get("change_pct", 0),
                "mcap_yi": q.get("mcap_yi", 0),
                "prem_pct": 0.0,
                "turnover_pct": q.get("turnover_pct", 0),
                "details": quality.get("details", {}),
            }
            results["ranked"].append(entry)
            results["success"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{code}: {str(e)}")

    # 排序
    results["ranked"].sort(key=lambda x: (-x["total_score"], -x.get("mcap_yi", 0)))
    for i, item in enumerate(results["ranked"]):
        item["rank"] = i + 1

    # 最佳
    if results["ranked"]:
        best = results["ranked"][0]
        results["best"] = {"code": best["code"], "name": best["name"], "score": best["total_score"]}

    # 摘要
    results["summary"] = (
        f"筛选{results['total']}只ETF，{results['success']}成功{results['failed']}失败。"
        f"最佳: {results['best']['name']}({results['best']['code']}) 评分{results['best']['score']}/5"
        if results["best"] else f"筛选{results['total']}只，全部失败"
    )

    return results


def screen_category(category_name, use_cache=True):
    """
    按分类筛选ETF。

    参数：
        category_name — 分类名，如 "宽基"、"行业半导体"

    返回 screen_etfs 的结果，如果分类不存在返回含错误信息的 dict。
    """
    codes = ETF_CATEGORIES.get(category_name)
    if not codes:
        # 尝试模糊匹配
        matched = [k for k in ETF_CATEGORIES if category_name in k]
        if matched:
            codes = ETF_CATEGORIES[matched[0]]
        else:
            return {"total": 0, "success": 0, "failed": 0,
                    "errors": [f"分类 '{category_name}' 不存在"],
                    "ranked": [], "best": None,
                    "summary": f"分类 '{category_name}' 不存在"}
    return screen_etfs(codes, use_cache)
