"""对TOP基金做精准分析 - 含完整风险指标"""

import sys, time
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_provider.akshare_fetcher import AkshareFetcher
from data_provider.manager import DataProviderManager
from analysis_engine.metrics import calculate_performance_metrics, calculate_risk_metrics, calculate_comprehensive_score
from analysis_engine.scorer import FundScoreResult

TOP_CODES = [
    "540010", "501097", "470006", "501095", "501200", "501098",
    "400015", "398051", "160144", "519193"
]

fetcher = AkshareFetcher()
provider = DataProviderManager(fetcher)
results = []

print(f"精准分析 {len(TOP_CODES)} 只基金...\n")

for i, code in enumerate(TOP_CODES):
    try:
        print(f"{i+1}/{len(TOP_CODES)} 分析 {code}...", end=" ")
        data = provider.get_fund_full_data(code)
        name = data.basic_info.fund_name

        if not data.nav_history or len(data.nav_history) < 20:
            print(f"X (净值不足)")
            continue

        perf = calculate_performance_metrics(data.nav_history)
        risk = calculate_risk_metrics(data.nav_history)
        score, rating = calculate_comprehensive_score(
            perf, risk, data.ranking, data.manager_info, data.fee
        )

        result = {
            "基金代码": code,
            "基金简称": name,
            "基金类型": data.basic_info.fund_type,
            "评分": score,
            "评级": rating,
            "近1月(%)": perf.return_1m,
            "近3月(%)": perf.return_3m,
            "近1年(%)": perf.return_1y,
            "年化收益(%)": perf.annualized_return,
            "最大回撤(%)": risk.max_drawdown,
            "夏普比率": risk.sharpe_ratio,
            "年化波动(%)": risk.annualized_volatility,
        }
        results.append(result)
        emoji = {"推荐": "🟢", "观望": "🟡", "谨慎": "🔴"}.get(rating, "?")
        print(f"{name[:20]} {emoji} {rating} 评分{score}")
        time.sleep(1)

    except Exception as e:
        print(f"X ({e})")

if results:
    df = pd.DataFrame(results)
    df = df.sort_values("评分", ascending=False)
    for i, idx in enumerate(df.index):
        df.at[idx, "排名"] = i + 1

    out = Path.home() / "Desktop/TOP基金精准评分.xlsx"
    df.to_excel(out, index=False)
    print(f"\n已保存: {out}")

    print(f"\n{'='*65}")
    print("TOP 基金精准评分排名:")
    print(f"{'='*65}")
    for _, row in df.iterrows():
        e = {"推荐": "🟢", "观望": "🟡", "谨慎": "🔴"}.get(row["评级"], "?")
        print(f"{e} #{int(row['排名']):2d} {row['基金代码']} {str(row['基金简称'])[:30]:30s} "
              f"评分:{int(row['评分']):3d}  回撤:{row['最大回撤(%)']:>6.1f}%  "
              f"1年:{row['近1年(%)']:+.1f}%")
