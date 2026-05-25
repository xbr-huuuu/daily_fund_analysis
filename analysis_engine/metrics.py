"""基金指标计算 - 纯数学计算，无外部依赖"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import numpy as np

from data_provider.models import FundFee, FundRanking, ManagerInfo, NavRecord


@dataclass
class PerformanceMetrics:
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_6m: Optional[float] = None
    return_1y: Optional[float] = None
    return_ytd: Optional[float] = None
    annualized_return: Optional[float] = None


@dataclass
class RiskMetrics:
    annualized_volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    win_rate: Optional[float] = None


# ---- 业绩计算 ----

def _get_return_between(nav_records: list[NavRecord], days: int) -> Optional[float]:
    if not nav_records or len(nav_records) < 2:
        return None
    cutoff = date.today() - timedelta(days=days)
    latest = nav_records[-1]
    for r in nav_records:
        if r.date >= cutoff:
            return round((latest.nav - r.nav) / r.nav * 100, 2) if r.nav > 0 else None
    return None


def calculate_performance_metrics(nav_records: list[NavRecord]) -> PerformanceMetrics:
    if not nav_records or len(nav_records) < 2:
        return PerformanceMetrics()

    perf = PerformanceMetrics()
    perf.return_1m = _get_return_between(nav_records, 30)
    perf.return_3m = _get_return_between(nav_records, 90)
    perf.return_6m = _get_return_between(nav_records, 180)
    perf.return_1y = _get_return_between(nav_records, 365)

    # 今年来
    year_start = date(date.today().year, 1, 1)
    for r in nav_records:
        if r.date >= year_start:
            perf.return_ytd = round((nav_records[-1].nav - r.nav) / r.nav * 100, 2) if r.nav > 0 else None
            break

    # 年化
    first, last = nav_records[0], nav_records[-1]
    span = (last.date - first.date).days
    if span > 0 and first.nav > 0:
        perf.annualized_return = round(((last.nav / first.nav) ** (365.0 / span) - 1) * 100, 2)

    return perf


# ---- 风险计算 ----

def calculate_risk_metrics(nav_records: list[NavRecord], risk_free_rate: float = 0.025) -> RiskMetrics:
    if not nav_records or len(nav_records) < 10:
        return RiskMetrics()

    navs = np.array([r.nav for r in nav_records])
    daily_returns = np.diff(navs) / navs[:-1]
    risk = RiskMetrics()

    # 年化波动率
    daily_vol = np.std(daily_returns, ddof=1)
    risk.annualized_volatility = round(float(daily_vol * math.sqrt(252) * 100), 2) if daily_vol > 0 else 0.0

    # 最大回撤
    peak = np.maximum.accumulate(navs)
    dd = (peak - navs) / peak
    risk.max_drawdown = round(float(np.max(dd) * 100), 2)

    # 夏普比率
    daily_rf = risk_free_rate / 252
    excess = daily_returns - daily_rf
    if daily_vol > 0:
        risk.sharpe_ratio = round(float(np.mean(excess) / daily_vol * math.sqrt(252)), 2)

    # 卡玛比率 = 年化收益 / 最大回撤（回撤用小数）
    if risk.max_drawdown and risk.max_drawdown > 0 and len(nav_records) >= 2:
        f, l = nav_records[0].nav, nav_records[-1].nav
        span = (nav_records[-1].date - nav_records[0].date).days
        if span > 0 and f > 0:
            ann_ret = (l / f) ** (365.0 / span) - 1
            risk.calmar_ratio = round(ann_ret / (risk.max_drawdown / 100.0), 2)

    # 索提诺比率
    downside = daily_returns[daily_returns < 0]
    if len(downside) > 0:
        d_vol = np.std(downside, ddof=1)
        if d_vol > 0:
            risk.sortino_ratio = round(float(np.mean(excess) / d_vol * math.sqrt(252)), 2)

    # 月度胜率
    if len(daily_returns) >= 21:
        wins = 0
        months = 0
        for i in range(0, len(daily_returns), 21):
            chunk = daily_returns[i:i + 21]
            if len(chunk) >= 5:
                months += 1
                if np.prod(1 + chunk) > 1:
                    wins += 1
        if months > 0:
            risk.win_rate = round(wins / months * 100, 1)

    return risk


# ---- 综合评分 ----

def _linear_score(value: float, worst: float, best: float) -> float:
    """线性映射到 0-100: worst→0, best→100"""
    if value <= worst:
        return 0.0
    if value >= best:
        return 100.0
    return (value - worst) / (best - worst) * 100.0


def calculate_comprehensive_score(
    performance: PerformanceMetrics,
    risk: RiskMetrics,
    ranking: Optional[FundRanking] = None,
    manager: Optional[ManagerInfo] = None,
    fee: Optional[FundFee] = None,
) -> tuple[int, str]:
    """
    五维度加权评分 (0-100)

    业绩 35% + 风险 25% + 排名 15% + 经理 15% + 费用 10%
    """

    # === 1. 业绩表现 (35分) ===
    perf_sub = 0.0
    perf_w = 0.0
    # 使用更合理的评分区间：-15%→0分, +30%→100分
    for ret, w in [
        (performance.return_1m, 0.10),
        (performance.return_3m, 0.20),
        (performance.return_6m, 0.20),
        (performance.return_1y, 0.30),
        (performance.return_ytd, 0.20),
    ]:
        if ret is not None:
            perf_sub += _linear_score(ret, worst=-15, best=30) * w
            perf_w += w

    perf_score = (perf_sub / perf_w * 0.35) if perf_w > 0 else 17.5

    # === 2. 风险控制 (25分) ===
    risk_sub = 0.0
    risk_w = 0.0

    if risk.max_drawdown is not None:
        risk_sub += _linear_score(-risk.max_drawdown, worst=-35, best=-5) * 0.4
        risk_w += 0.4

    if risk.sharpe_ratio is not None:
        risk_sub += _linear_score(risk.sharpe_ratio, worst=-0.5, best=2.0) * 0.3
        risk_w += 0.3

    if risk.calmar_ratio is not None:
        risk_sub += _linear_score(risk.calmar_ratio, worst=-1.0, best=3.0) * 0.3
        risk_w += 0.3

    risk_score = (risk_sub / risk_w * 0.25) if risk_w > 0 else 12.5

    # === 3. 排名分位 (15分) ===
    if ranking and ranking.percentile is not None:
        rank_score = _linear_score(100 - ranking.percentile, worst=0, best=90) * 0.15
    else:
        rank_score = 7.5

    # === 4. 基金经理 (15分) ===
    if manager:
        mgr_sub = 0.0
        mgr_w = 0.0
        if manager.tenure_start:
            years = (date.today() - manager.tenure_start).days / 365.0
            mgr_sub += _linear_score(years, worst=0.5, best=5) * 0.5
            mgr_w += 0.5
        if manager.total_return is not None:
            mgr_sub += _linear_score(manager.total_return, worst=-10, best=100) * 0.5
            mgr_w += 0.5
        mgr_score = (mgr_sub / mgr_w * 0.15) if mgr_w > 0 else 7.5
    else:
        mgr_score = 7.5

    # === 5. 费用成本 (10分) ===
    if fee:
        total_fee = (fee.management_fee or 0) + (fee.custody_fee or 0) + (fee.sales_service_fee or 0)
        if total_fee > 0:
            fee_score = _linear_score(1.5 - total_fee, worst=-0.5, best=1.2) * 0.10
        else:
            fee_score = 5.0
    else:
        fee_score = 5.0

    total = round(perf_score + risk_score + rank_score + mgr_score + fee_score)
    total = max(0, min(100, total))

    if total >= 75:
        rating = "推荐"
    elif total >= 55:
        rating = "观望"
    else:
        rating = "谨慎"

    return total, rating
