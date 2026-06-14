# etf-fund-analysis
etf-fund-analysis is a Chinese A-share ETF and mutual fund analysis skill designed for fund evaluation, fee comparison, portfolio holdings analysis, and performance benchmarking.

Key features:


Fund type classification — automatically routes analysis based on fund category: ETF (tracks index), LOF (hybrid on-exchange), active fund (manager-driven), or money/bond fund. Defaults to ETF analysis.


Analysis dimension routing — supports four entry points: full evaluation (fees + holdings + performance + tracking error), holdings breakdown ("what stocks does this fund own"), performance comparison ("how has it performed"), and fee comparison ("is it expensive").


Three-tier data sourcing — primary data through Tencent quotes (price, scale, turnover) + East Money fund API (NAV, holdings, fees, performance history); secondary via wiki knowledge base for past analysis records; tertiary via web search for fund announcements and clearance risk alerts.


ETF quality scoring system — 5-point weighted score: low fee (+1), low tracking error (+1), large scale >50B (+1), normal premium/discount (+1), turnover >1% (+1). Score bands: ≥4=recommended, 3=acceptable, ≤2=not recommended.


Holdings scanning & portfolio analysis — batch-scans TOP10 constituent stocks via tencent_quote() for PE/PB/market cap/daily change. Outputs top 5 holdings with name, weight, and valuation metrics. Determines portfolio style (value/growth/balanced), concentration (single stock >20% flagged as high risk), and sector distribution.


Liquidity & clearance risk detection — flags ETFs with scale <50M RMB as approaching regulatory clearance threshold (5000 万连续 20 日). Auto-triggers web search for clearance announcements when scale <5000 万 or trending downward. Adjusts turnover interpretation for small-scale funds (high turnover may be illusory due to small base).


Peer comparison — side-by-side comparison with competing funds tracking the same index: fee rate, scale, 1-year return, tracking error, daily turnover. Identifies and recommends the optimal fund in each category.


Index attribution — when underlying index moves >1% intraday, automatically searches for the reason and attributes ETF performance to sector/stock drivers.


Fund types covered: ETFs, LOFs, actively managed funds, money market, bond funds. Output templates differentiate passive (tracking error, premium/discount) vs active (manager track record, excess returns) evaluation frameworks.
