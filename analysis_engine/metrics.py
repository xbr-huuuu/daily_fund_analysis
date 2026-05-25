"""基金指标计算 - 纯数学计算，无外部依赖"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import numpy as np

from data_provider.models import FundFee, FundRanking, ManagerInfo, NavRecord


@dataclass
class PerformanceMetrics:
    """业绩表现指标"""
    return_1m: Optional[float] = None       # 近1月收益率(%)
    return_3m: Optional[float] = None       # 近3月收益率(%)
    return_6m: Optional[float] = None       # 近6月收益率(%)
    return_1y: Optional[float] = None       # 近1年收益率(%)
    return_ytd: Optional[float] = None      # 今年来收益率(%)
    annualized_return: Optional[float] = None  # 年化收益率(%)


@dataclass
class RiskMetrics:
    """风险指标"""
    annualized_volatility: Optional[float] = None  # 年化波动率(%)
    max_drawdown: Optional[float] = None           # 最大回撤(%)
    sharpe_ratio: Optional[float] = None           # 夏普比率
    calmar_ratio: Optional[float] = None           # 卡玛比率
    sortino_ratio: Optional[float] = None          # 索提诺比率
    win_rate: Optional[float] = None               # 月度胜率(%)


def _get_return_between(nav_records: list[NavRecord], days: int) -> Optional[float]:
    """计算指定天数区间的收益率"""
    if not nav_records or len(nav_records) < 2:
        return None

    today = date.today()
    start_date = today - timedelta(days=days)

    # 找到最近的净值
    latest = nav_records[-1]
    # 找到目标日期之前最近的净值
    target_nav = None
    for record in nav_records:
        if record.date >= start_date:
            target_nav = record
            break

    if target_nav is None or target_nav.nav == 0:
        return None

    return round((latest.nav - target_nav.nav) / target_nav.nav * 100, 2)


def calculate_performance_metrics(nav_records: list[NavRecord]) -> PerformanceMetrics:
    """计算各时间区间的收益率"""
    if not nav_records or len(nav_records) < 2:
        return PerformanceMetrics()

    perf = PerformanceMetrics()
    perf.return_1m = _get_return_between(nav_records, 30)
    perf.return_3m = _get_return_between(nav_records, 90)
    perf.return_6m = _get_return_between(nav_records, 180)
    perf.return_1y = _get_return_between(nav_records, 365)

    # 今年来收益率
    today = date.today()
    year_start = date(today.year, 1, 1)
    year_start_nav = None
    for record in nav_records:
        if record.date >= year_start:
            year_start_nav = record
            break
    if year_start_nav and year_start_nav.nav > 0:
        perf.return_ytd = round(
            (nav_records[-1].nav - year_start_nav.nav) / year_start_nav.nav * 100, 2
        )

    # 年化收益率
    if len(nav_records) >= 2:
        first = nav_records[0]
        last = nav_records[-1]
        days = (last.date - first.date).days
        if days > 0 and first.nav > 0:
            total_return = last.nav / first.nav
            perf.annualized_return = round((total_return ** (365 / days) - 1) * 100, 2)

    return perf


def calculate_risk_metrics(
    nav_records: list[NavRecord],
    risk_free_rate: float = 0.025,
) -> RiskMetrics:
    """从净值序列计算风险指标"""
    if not nav_records or len(nav_records) < 10:
        return RiskMetrics()

    # 日收益率序列
    navs = np.array([r.nav for r in nav_records])
    daily_returns = np.diff(navs) / navs[:-1]

    risk = RiskMetrics()

    # 年化波动率
    daily_vol = np.std(daily_returns, ddof=1)
    risk.annualized_volatility = round(daily_vol * math.sqrt(252) * 100, 2)

    # 最大回撤
    peak = np.maximum.accumulate(navs)
    drawdown = (peak - navs) / peak
    risk.max_drawdown = round(np.max(drawdown) * 100, 2)

    # 夏普比率
    daily_rf = risk_free_rate / 252
    excess_returns = daily_returns - daily_rf
    if daily_vol > 0:
        risk.sharpe_ratio = round(
            np.mean(excess_returns) / daily_vol * math.sqrt(252), 2
        )

    # 年化收益率 (用于卡玛比率)
    annualized_return = None
    if len(nav_records) >= 2:
        first_nav = nav_records[0].nav
        last_nav = nav_records[-1].nav
        days = (nav_records[-1].date - nav_records[0].date).days
        if days > 0 and first_nav > 0:
            annualized_return = (last_nav / first_nav) ** (365 / days) - 1

    # 卡玛比率 = 年化收益 / 最大回撤
    if annualized_return is not None and risk.max_drawdown and risk.max_drawdown > 0:
        risk.calmar_ratio = round(annualized_return / (risk.max_drawdown / 100), 2)

    # 索提诺比率
    downside_returns = daily_returns[daily_returns < 0]
    if len(downside_returns) > 0:
        downside_vol = np.std(downside_returns, ddof=1)
        if downside_vol > 0:
            risk.sortino_ratio = round(
                np.mean(excess_returns) / downside_vol * math.sqrt(252), 2
            )

    # 月度胜率
    monthly_returns = []
    for i in range(0, len(daily_returns), 21):  # 约一个月
        month_ret = np.prod(1 + daily_returns[i:i+21]) - 1
        monthly_returns.append(month_ret)
    if monthly_returns:
        risk.win_rate = round(
            sum(1 for r in monthly_returns if r > 0) / len(monthly_returns) * 100, 1
        )

    return risk


def calculate_comprehensive_score(
    performance: PerformanceMetrics,
    risk: RiskMetrics,
    ranking: Optional[FundRanking] = None,
    manager: Optional[ManagerInfo] = None,
    fee: Optional[FundFee] = None,
) -> tuple[int, str]:
    """
    综合评分 (0-100) + 评级

    评分权重:
    - 业绩表现: 35%
    - 风险控制: 25%
    - 排名分位: 15%
    - 基金经理: 15%
    - 费用成本: 10%
    """
    total_score = 0.0

    # 1. 业绩表现 (35分)
    perf_score = 0.0
    perf_count = 0
    # 各区间收益评分: 满分标准 >20% 得满分, <-10% 得0分
    for ret, weight in [
        (performance.return_1m, 0.15),
        (performance.return_3m, 0.20),
        (performance.return_6m, 0.25),
        (performance.return_1y, 0.25),
        (performance.return_ytd, 0.15),
    ]:
        if ret is not None:
            score = max(0, min(100, (ret + 10) / 30 * 100))
            perf_score += score * weight
            perf_count += weight
    if perf_count > 0:
        total_score += (perf_score / perf_count) * 0.35

    # 2. 风险控制 (25分)
    risk_score = 0.0
    risk_count = 0
    # 最大回撤: <10% 满分, >30% 零分
    if risk.max_drawdown is not None:
        dd_score = max(0, min(100, (30 - risk.max_drawdown) / 20 * 100))
        risk_score += dd_score * 0.4
        risk_count += 0.4
    # 夏普比率: >1.5 满分, <0 零分
    if risk.sharpe_ratio is not None:
        sharpe_score = max(0, min(100, risk.sharpe_ratio / 1.5 * 100))
        risk_score += sharpe_score * 0.4
        risk_count += 0.4
    # 波动率: <15% 满分, >35% 零分
    if risk.annualized_volatility is not None:
        vol_score = max(0, min(100, (35 - risk.annualized_volatility) / 20 * 100))
        risk_score += vol_score * 0.2
        risk_count += 0.2
    if risk_count > 0:
        total_score += (risk_score / risk_count) * 0.25

    # 3. 排名分位 (15分)
    if ranking and ranking.percentile is not None:
        # 前10% 满分, 后50% 零分
        rank_score = max(0, min(100, (50 - ranking.percentile) / 40 * 100))
        total_score += rank_score * 0.15
    else:
        total_score += 7.5  # 无数据给中间分

    # 4. 基金经理 (15分)
    if manager:
        mgr_score = 50.0  # 基础分
        # 任职年限加分
        if manager.tenure_start:
            years = (date.today() - manager.tenure_start).days / 365
            if years >= 3:
                mgr_score += 30
            elif years >= 1:
                mgr_score += 15
        # 历史回报加分
        if manager.total_return is not None and manager.total_return > 0:
            mgr_score += min(20, manager.total_return / 5)
        total_score += min(100, mgr_score) * 0.15
    else:
        total_score += 7.5  # 无数据给中间分

    # 5. 费用成本 (10分)
    if fee:
        # 管理费+托管费: <0.6% 满分, >1.5% 零分
        total_fee = 0.0
        if fee.management_fee is not None:
            total_fee += fee.management_fee
        if fee.custody_fee is not None:
            total_fee += fee.custody_fee
        if fee.sales_service_fee is not None:
            total_fee += fee.sales_service_fee
        if total_fee > 0:
            fee_score = max(0, min(100, (1.5 - total_fee) / 0.9 * 100))
            total_score += fee_score * 0.10
        else:
            total_score += 5.0
    else:
        total_score += 5.0  # 无数据给中间分

    # 取整
    final_score = int(round(total_score))

    # 评级
    if final_score >= 75:
        rating = "推荐"
    elif final_score >= 55:
        rating = "观望"
    else:
        rating = "谨慎"

    return final_score, rating
