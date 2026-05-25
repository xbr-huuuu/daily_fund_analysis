"""卖出/减仓策略"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExitAdvice:
    """卖出建议"""
    fund_code: str
    fund_name: str
    action: str          # "持有" / "减仓" / "清仓"
    action_emoji: str    # "✅" / "⚠️" / "🚨"
    score: int
    rating: str
    drawdown: Optional[float]
    reason: str


def evaluate_exit(
    fund_code: str,
    fund_name: str,
    score: int,
    rating: str,
    max_drawdown: Optional[float],
    manager_changed: bool = False,
    prev_score: Optional[int] = None,
    held: bool = False,
) -> ExitAdvice:
    """
    卖出/减仓评估

    触发减仓的条件:
    1. 评分 < 45 (谨慎下线): 建议清仓
    2. 评分 45-55 (谨慎): 建议减仓
    3. 评分从推荐掉到观望: 注意观察
    4. 回撤 > 30%: 风险警告
    5. 基金经理变动: 重新评估
    """

    # 清仓条件
    if score < 45:
        if max_drawdown and max_drawdown > 30:
            reason = "评分极低且回撤超30%，双重风险，建议清仓止损"
        else:
            reason = "评分持续低迷，基金基本面恶化，建议清仓"
        return ExitAdvice(
            fund_code=fund_code, fund_name=fund_name,
            action="清仓", action_emoji="🚨",
            score=score, rating=rating, drawdown=max_drawdown,
            reason=reason,
        )

    # 减仓条件
    if score < 55:
        if max_drawdown and max_drawdown > 25:
            reason = "评分偏低伴随大幅回撤，建议减仓50%控制风险"
        else:
            reason = "评分不足，建议减仓30%观望"
        return ExitAdvice(
            fund_code=fund_code, fund_name=fund_name,
            action="减仓", action_emoji="⚠️",
            score=score, rating=rating, drawdown=max_drawdown,
            reason=reason,
        )

    # 评分下降警告
    if prev_score and rating == "观望" and prev_score >= 75:
        reason = f"评分从{prev_score}降至{score}，趋势转弱，注意观察"
        return ExitAdvice(
            fund_code=fund_code, fund_name=fund_name,
            action="观察", action_emoji="👀",
            score=score, rating=rating, drawdown=max_drawdown,
            reason=reason,
        )

    # 经理变动警告
    if manager_changed:
        reason = "基金经理发生变动！建议观察1-2个月再决定"
        return ExitAdvice(
            fund_code=fund_code, fund_name=fund_name,
            action="观察", action_emoji="👀",
            score=score, rating=rating, drawdown=max_drawdown,
            reason=reason,
        )

    # 未持仓基金 - 买入建议
    if not held:
        if rating == "推荐" and score >= 75:
            if max_drawdown and max_drawdown > 10:
                reason = f"评分{score}，当前回撤{max_drawdown:.1f}%，低估区间，建议开始建仓"
                return ExitAdvice(
                    fund_code=fund_code, fund_name=fund_name,
                    action="买入建仓", action_emoji="💰",
                    score=score, rating=rating, drawdown=max_drawdown,
                    reason=reason,
                )
            else:
                reason = f"评分{score}，表现优秀，可考虑建仓"
                return ExitAdvice(
                    fund_code=fund_code, fund_name=fund_name,
                    action="可买入", action_emoji="📊",
                    score=score, rating=rating, drawdown=max_drawdown,
                    reason=reason,
                )
        elif rating == "观望":
            reason = "评分中等，建议等待评分回升或回撤扩大再入场"
            return ExitAdvice(
                fund_code=fund_code, fund_name=fund_name,
                action="暂不买入", action_emoji="⏳",
                score=score, rating=rating, drawdown=max_drawdown,
                reason=reason,
            )
        else:
            reason = "评分偏低，不建议现在入场"
            return ExitAdvice(
                fund_code=fund_code, fund_name=fund_name,
                action="不建议买", action_emoji="🚫",
                score=score, rating=rating, drawdown=max_drawdown,
                reason=reason,
            )

    # 正常持有
    if rating == "推荐":
        reason = "评分良好，建议继续持有并定投"
    else:
        reason = "表现正常，暂时持有观察"

    return ExitAdvice(
        fund_code=fund_code, fund_name=fund_name,
        action="持有", action_emoji="✅",
        score=score, rating=rating, drawdown=max_drawdown,
        reason=reason,
    )


def format_exit_report(advice: ExitAdvice) -> str:
    """格式化操作建议"""
    dd_str = f"{advice.drawdown:.1f}%" if advice.drawdown else "-"
    lines = [
        f"**{advice.action_emoji} {advice.fund_name}：{advice.action}** — {advice.reason}",
    ]
    return "\n".join(lines)
