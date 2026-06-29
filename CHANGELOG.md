# 变更记录

格式：`v主版本.次版本.修订号`，规则：
- **主版本**（x.0.0）：架构优化或重构
- **次版本**（0.x.0）：功能模块增减
- **修订号**（0.0.x）：Bug修复或模块内部优化

---

## v2.2.0 (2026-06-26)

- G1: fund_data.py 新增 dca_simulate() — 定投回算器（月投/总额/收益率/年化/vs一次性）
- G2: tracker.py 新增 check_style_drift() — 风格漂移检测；track_fund() 新增 style 参数
- G3: fund_data.py 新增 try_fetch_fund_info() — 尽力获取净值/费率（腾讯+天天基金双通道）

## v2.1.0 (2026-06-26)

- F1: fund_data.py 新增 compute_returns() / compute_risk_metrics() / compute_all_metrics() — 从K线数据回算收益率、最大回撤、波动率、夏普比率
- F2: 新增 scripts/screener.py — 批量ETF筛选（screen_etfs / screen_category），覆盖8类预设ETF
- F3: fund_data.py 新增 lof_arbitrage_signal() — LOF折溢价套利信号检测

## v2.0.0 (2026-06-26)

- E1: scripts/fund_data.py — 自建基金数据层（tencent_quote, calc_premium, classify_style, summarize_fund_data）
- E2: scripts/scoring.py — ETF 5项质量评分（费率/跟踪误差/规模/折溢价/流动性）
- E3: scripts/holdings.py — 持仓风险分析（集中度/风格/高PE/亏损股检测）
- E4: scripts/peer.py — 同类ETF自动对比（ETF_PEER_MAP + compare_peers）
- E5: scripts/cache.py — 文件缓存系统（行情5min/基金1h/持仓24h）
- E6: scripts/tracker.py — ETF追踪记录与预警（规模/折溢价异常检测）

## v1.0.0 (初始版本)

初始发布版。
