"""批量基金评分 - 使用排名接口，避免反爬"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

INPUT_FILE = Path.home() / "Desktop/精选基金列表.xlsx"
OUTPUT_FILE = Path.home() / "Desktop/基金评分排名.xlsx"
TOP_N = 20


def score_from_rank(df_rank):
    """基于排名数据打分，不逐只调接口"""

    scores = []
    for _, row in df_rank.iterrows():
        code = str(row.get("基金代码", ""))
        name = str(row.get("基金简称", ""))
        ftype = str(row.get("基金类型", ""))

        # 提取各区间收益
        r1m = _safe(row.get("近1月", row.get("近1月收益率", 0)))
        r3m = _safe(row.get("近3月", row.get("近3月收益率", 0)))
        r6m = _safe(row.get("近6月", row.get("近6月收益率", 0)))
        r1y = _safe(row.get("近1年", row.get("近1年收益率", 0)))
        r2y = _safe(row.get("近2年", row.get("近2年收益率", 0)))
        r3y = _safe(row.get("近3年", row.get("近3年收益率", 0)))

        # 简单评分：多区间收益加权
        perf_score = 0
        count = 0
        for ret, w in [(r1m, 0.15), (r3m, 0.20), (r6m, 0.25), (r1y, 0.25), (r2y, 0.1), (r3y, 0.05)]:
            if ret is not None and not np.isnan(ret):
                s = max(0, min(100, (ret + 10) / 30 * 100))
                perf_score += s * w
                count += w
        if count > 0:
            perf_score = perf_score / count * 35
        else:
            perf_score = 0

        # 简单风险加分
        risk_score = 25  # 无条件给基础分

        # 排名加分
        rank_score = 0
        total = len(df_rank)
        if total > 0:
            idx = df_rank.index.get_loc(row.name)
            pct = (idx + 1) / total * 100
            rank_score = max(0, min(100, (50 - pct) / 40 * 100)) * 0.15

        # 基础分
        mgr_score = 7.5
        fee_score = 5.0

        total_score = round(perf_score + risk_score + rank_score + mgr_score + fee_score)
        total_score = max(0, min(100, total_score))

        if total_score >= 75:
            rating = "推荐"
        elif total_score >= 55:
            rating = "观望"
        else:
            rating = "谨慎"

        scores.append({
            "基金代码": code,
            "基金简称": name,
            "基金类型": ftype,
            "评分": total_score,
            "评级": rating,
            "近1月(%)": _fmt(r1m),
            "近3月(%)": _fmt(r3m),
            "近6月(%)": _fmt(r6m),
            "近1年(%)": _fmt(r1y),
        })

    scores.sort(key=lambda x: x["评分"], reverse=True)
    for i, s in enumerate(scores):
        s["排名"] = i + 1
    return scores


def _safe(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _fmt(val):
    if val is None:
        return None
    return round(val, 2)


def main():
    # 读取目标基金列表
    target = pd.read_excel(INPUT_FILE)
    target_codes = set(target["基金代码"].astype(str))
    print(f"目标基金: {len(target_codes)} 只\n")

    all_results = []
    rank_types = ["股票型", "混合型"]

    for rt in rank_types:
        print(f"获取 {rt} 排名数据...")
        try:
            import akshare as ak
            time.sleep(0.5)
            df = ak.fund_open_fund_rank_em(symbol=rt)
            if df is None or df.empty:
                print(f"  {rt}: 无数据")
                continue
            print(f"  {rt}: {len(df)} 只")

            # 只看我们关心的
            df_filtered = df[df["基金代码"].astype(str).isin(target_codes)]
            print(f"  在目标列表中: {len(df_filtered)} 只")

            if not df_filtered.empty:
                s = score_from_rank(df_filtered)
                all_results.extend(s)

        except Exception as e:
            print(f"  {rt} 失败: {e}")

    if not all_results:
        print("\n没有成功评分的基金")
        return

    df_out = pd.DataFrame(all_results)
    df_out = df_out.sort_values("评分", ascending=False)
    for i, idx in enumerate(df_out.index):
        df_out.at[idx, "排名"] = i + 1

    df_out.to_excel(OUTPUT_FILE, index=False)
    print(f"\n共评分 {len(all_results)} 只基金")
    print(f"已保存: {OUTPUT_FILE}")

    top = df_out.head(TOP_N)
    print(f"\n{'='*70}")
    print(f"TOP {TOP_N}:")
    print(f"{'='*70}")
    for _, row in top.iterrows():
        emoji = {"推荐": "🟢", "观望": "🟡", "谨慎": "🔴"}.get(row["评级"], "⚪")
        print(f"{emoji} #{int(row['排名']):3d} {row['基金代码']} {str(row['基金简称'])[:25]:25s} "
              f"评分:{int(row['评分']):3d}  近1年:{row.get('近1年(%)', '?'):>6}")

    print(f"\n推荐代码 (加进 .env):")
    codes = ",".join(str(c) for c in top["基金代码"].tolist()[:TOP_N])
    print(codes)


if __name__ == "__main__":
    main()
