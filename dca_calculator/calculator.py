"""智能定投计算器 - 低估多投、高估少投"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class DcaPlan:
    """定投计划配置"""
    fund_code: str
    fund_name: str
    total_budget: float          # 总预算(元)
    invested: float              # 已投入(元)
    remaining: float             # 剩余可投(元)
    base_amount: float           # 基准每期投入(元)


@dataclass
class DcaAdvice:
    """单期定投建议"""
    fund_code: str
    fund_name: str
    current_drawdown: float      # 当前回撤(%)
    multiplier: float            # 投入倍数
    suggested_amount: float      # 建议投入金额(元)
    reason: str                  # 建议理由
    trend_emoji: str             # 趋势图标


def calculate_dca_advice(
    fund_code: str,
    fund_name: str,
    current_drawdown: float,
    remaining_budget: float,
    plan_months: int = 12,
) -> DcaAdvice:
    """
    根据当前回撤计算定投建议

    策略：
    - 回撤 > 30%: 3倍投入 (极度低估，大胆加仓)
    - 回撤 20-30%: 2倍投入 (低估，积极买入)
    - 回撤 10-20%: 1.5倍投入 (偏低估，适度加仓)
    - 回撤 5-10%: 1倍投入 (正常定投)
    - 回撤 < 5%: 0.5倍投入 (偏高，少量买入)
    - 盈利(回撤负数): 0.25倍投入 (高位，暂停大额买入)
    """

    base = remaining_budget / max(plan_months, 1)

    if current_drawdown > 30:
        multiplier = 3.0
        reason = "回撤超30%，极度低估，建议大额加仓"
        emoji = "💰💰💰"
    elif current_drawdown > 20:
        multiplier = 2.0
        reason = "回撤20-30%，明显低估，建议积极买入"
        emoji = "💰💰"
    elif current_drawdown > 10:
        multiplier = 1.5
        reason = "回撤10-20%，偏低估，可适度加仓"
        emoji = "💰"
    elif current_drawdown > 5:
        multiplier = 1.0
        reason = "小幅回撤，正常定投节奏"
        emoji = "📊"
    elif current_drawdown >= 0:
        multiplier = 0.5
        reason = "净值偏高，建议少量买入等待回调"
        emoji = "⏳"
    else:
        # 盈利中
        multiplier = 0.25
        reason = "处于盈利区间，暂缓大额买入，小额定投维持"
        emoji = "⏸️"

    suggested = round(base * multiplier, 2)
    # 不超过剩余预算
    suggested = min(suggested, remaining_budget)

    return DcaAdvice(
        fund_code=fund_code,
        fund_name=fund_name,
        current_drawdown=current_drawdown,
        multiplier=multiplier,
        suggested_amount=suggested,
        reason=reason,
        trend_emoji=emoji,
    )


def format_dca_report(advice: DcaAdvice) -> str:
    """格式化定投建议报告"""
    lines = [
        f"### 💡 智能定投建议",
        f"",
        f"**{advice.trend_emoji} {advice.fund_name}**",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 当前回撤 | {advice.current_drawdown:.2f}% |",
        f"| 投入倍数 | {advice.multiplier:.1f}x |",
        f"| 本期建议投入 | **{advice.suggested_amount:.2f} 元** |",
        f"",
        f"**理由:** {advice.reason}",
    ]
    return "\n".join(lines)
