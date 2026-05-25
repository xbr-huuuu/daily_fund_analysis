"""综合评分与评级结果"""

from dataclasses import dataclass
from typing import Optional

from analysis_engine.metrics import PerformanceMetrics, RiskMetrics


@dataclass
class FundScoreResult:
    """基金评分结果"""
    fund_code: str
    fund_name: str
    score: int                  # 0-100
    rating: str                 # "推荐" / "观望" / "谨慎"
    rating_emoji: str           # "🟢" / "🟡" / "🔴"
    summary: str                # 一句话摘要
    performance: PerformanceMetrics
    risk: RiskMetrics

    @classmethod
    def create(
        cls,
        fund_code: str,
        fund_name: str,
        score: int,
        rating: str,
        performance: PerformanceMetrics,
        risk: RiskMetrics,
        summary: str = "",
    ) -> "FundScoreResult":
        """创建评分结果"""
        if rating == "推荐":
            emoji = "🟢"
        elif rating == "观望":
            emoji = "🟡"
        else:
            emoji = "🔴"

        if not summary:
            # 生成默认摘要
            if rating == "推荐":
                summary = "业绩优秀，风险可控"
            elif rating == "观望":
                summary = "表现中等，等待机会"
            else:
                summary = "风险较高，谨慎对待"

        return cls(
            fund_code=fund_code,
            fund_name=fund_name,
            score=score,
            rating=rating,
            rating_emoji=emoji,
            summary=summary,
            performance=performance,
            risk=risk,
        )


def format_performance_text(perf: PerformanceMetrics) -> str:
    """格式化业绩数据为文本"""
    lines = []
    if perf.return_1m is not None:
        lines.append(f"近1月: {perf.return_1m:+.2f}%")
    if perf.return_3m is not None:
        lines.append(f"近3月: {perf.return_3m:+.2f}%")
    if perf.return_6m is not None:
        lines.append(f"近6月: {perf.return_6m:+.2f}%")
    if perf.return_1y is not None:
        lines.append(f"近1年: {perf.return_1y:+.2f}%")
    if perf.return_ytd is not None:
        lines.append(f"今年来: {perf.return_ytd:+.2f}%")
    if perf.annualized_return is not None:
        lines.append(f"年化收益: {perf.annualized_return:+.2f}%")
    return "\n".join(lines) if lines else "暂无业绩数据"


def format_risk_text(risk: RiskMetrics) -> str:
    """格式化风险数据为文本"""
    lines = []
    if risk.annualized_volatility is not None:
        lines.append(f"年化波动率: {risk.annualized_volatility:.2f}%")
    if risk.max_drawdown is not None:
        lines.append(f"最大回撤: {risk.max_drawdown:.2f}%")
    if risk.sharpe_ratio is not None:
        lines.append(f"夏普比率: {risk.sharpe_ratio:.2f}")
    if risk.calmar_ratio is not None:
        lines.append(f"卡玛比率: {risk.calmar_ratio:.2f}")
    if risk.sortino_ratio is not None:
        lines.append(f"索提诺比率: {risk.sortino_ratio:.2f}")
    if risk.win_rate is not None:
        lines.append(f"月度胜率: {risk.win_rate:.1f}%")
    return "\n".join(lines) if lines else "暂无风险数据"
