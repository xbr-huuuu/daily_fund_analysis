"""LLM 报告生成器 - 使用 LiteLLM 统一网关"""

import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Optional

from config.settings import Settings
from data_provider.models import FundFullData
from analysis_engine.scorer import (
    FundScoreResult,
    format_performance_text,
    format_risk_text,
)

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "config" / "prompts" / "fund_analysis.txt"


def _load_prompt_template() -> str:
    """加载 prompt 模板"""
    try:
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error(f"Prompt 模板文件不存在: {PROMPT_TEMPLATE_PATH}")
        return ""


def _format_holdings(holdings) -> str:
    """格式化持仓数据"""
    if not holdings:
        return "暂无持仓数据"
    lines = []
    for h in holdings[:10]:
        lines.append(f"  {h.rank}. {h.stock_name}({h.stock_code}): {h.ratio:.2f}%")
    return "\n".join(lines)


def _format_industry(allocations) -> str:
    """格式化行业配置"""
    if not allocations:
        return "暂无行业配置数据"
    lines = []
    for a in allocations[:10]:
        lines.append(f"  - {a.industry}: {a.ratio:.2f}%")
    return "\n".join(lines)


def _format_manager(manager) -> str:
    """格式化基金经理信息"""
    if not manager:
        return "暂无基金经理信息"
    lines = [f"  姓名: {manager.name}"]
    if manager.tenure_start:
        years = (date.today() - manager.tenure_start).days / 365
        lines.append(f"  任职时间: {manager.tenure_start} (约{years:.1f}年)")
    if manager.fund_size:
        lines.append(f"  管理规模: {manager.fund_size:.2f}亿元")
    if manager.total_return is not None:
        lines.append(f"  任职回报: {manager.total_return:+.2f}%")
    if manager.fund_count:
        lines.append(f"  管理基金数: {manager.fund_count}")
    return "\n".join(lines)


def _format_fee(fee) -> str:
    """格式化费率信息"""
    if not fee:
        return "暂无费率数据"
    lines = []
    if fee.management_fee is not None:
        lines.append(f"  管理费: {fee.management_fee:.2f}%")
    if fee.custody_fee is not None:
        lines.append(f"  托管费: {fee.custody_fee:.2f}%")
    if fee.sales_service_fee is not None:
        lines.append(f"  销售服务费: {fee.sales_service_fee:.2f}%")
    if fee.purchase_fee is not None:
        lines.append(f"  申购费: {fee.purchase_fee:.2f}%")
    if fee.redemption_fee is not None:
        lines.append(f"  赎回费: {fee.redemption_fee:.2f}%")
    return "\n".join(lines) if lines else "暂无费率数据"


def _format_ranking(ranking) -> str:
    """格式化排名信息"""
    if not ranking:
        return "暂无排名数据"
    if ranking.rank and ranking.total:
        return f"  同类排名: {ranking.rank}/{ranking.total} (前{ranking.percentile:.1f}%)"
    return "暂无排名数据"


class ReportGenerator:
    """LLM 报告生成器"""

    # 常用模型 provider 前缀自动补全
    _PROVIDER_MAP = {
        "deepseek-chat": "deepseek/deepseek-chat",
        "deepseek-reasoner": "deepseek/deepseek-reasoner",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
        "claude-3-opus": "anthropic/claude-3-opus-20240229",
        "claude-3-sonnet": "anthropic/claude-3-sonnet-20240229",
        "claude-3-haiku": "anthropic/claude-3-haiku-20240307",
        "qwen-turbo": "openai/qwen-turbo",
        "qwen-plus": "openai/qwen-plus",
        "glm-4": "openai/glm-4",
    }

    def _normalize_model(self, model: str) -> str:
        """自动补全 liteLLM provider 前缀"""
        if "/" in model:
            return model
        return self._PROVIDER_MAP.get(model, f"openai/{model}")

    def __init__(self, config: Settings):
        self.config = config
        self.prompt_template = _load_prompt_template()
        self._primary_model = None
        self._fallback_model = None

    def _init_llm(self):
        """延迟初始化 LLM"""
        try:
            import litellm
            litellm.drop_params = True
            self._primary_model = True
            logger.info(f"LLM 主模型: {self.config.llm_primary_model}")
        except ImportError:
            logger.warning("litellm 未安装，将使用纯数字报告")

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM，支持主备模型故障转移"""
        if not self._primary_model:
            self._init_llm()

        if not self._primary_model:
            return None

        # 尝试主模型
        try:
            import litellm
            model = self._normalize_model(self.config.llm_primary_model)
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.config.llm_primary_api_key,
                api_base=self.config.llm_primary_base_url or None,
                max_tokens=self.config.llm_max_tokens,
                temperature=self.config.llm_temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"主模型调用失败: {e}")

        # 尝试备选模型
        if self.config.llm_fallback_api_key:
            try:
                import litellm
                model = self._normalize_model(self.config.llm_fallback_model)
                response = litellm.completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self.config.llm_fallback_api_key,
                    api_base=self.config.llm_fallback_base_url or None,
                    max_tokens=self.config.llm_max_tokens,
                    temperature=self.config.llm_temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"备选模型调用失败: {e}")

        return None

    def generate_single_report(
        self, fund_data: FundFullData, score: FundScoreResult
    ) -> str:
        """为单只基金生成详细分析报告"""
        if not self.prompt_template:
            return self._generate_fallback_report(fund_data, score)

        prompt = self.prompt_template.format(
            fund_name=fund_data.basic_info.fund_name,
            fund_code=fund_data.basic_info.fund_code,
            fund_type=fund_data.basic_info.fund_type,
            performance=format_performance_text(score.performance),
            risk=format_risk_text(score.risk),
            holdings=_format_holdings(fund_data.top_holdings),
            industry=_format_industry(fund_data.industry_allocation),
            manager=_format_manager(fund_data.manager_info),
            fee=_format_fee(fund_data.fee),
            ranking=_format_ranking(fund_data.ranking),
            score=score.score,
            rating=score.rating,
        )

        llm_response = self._call_llm(prompt)
        if llm_response:
            return llm_response

        # LLM 调用失败，降级为纯数字报告
        logger.info("LLM 调用失败，使用降级报告")
        return self._generate_fallback_report(fund_data, score)

    def _generate_fallback_report(
        self, fund_data: FundFullData, score: FundScoreResult
    ) -> str:
        """降级报告 - 纯数字，不依赖 LLM"""
        lines = [
            f"## {fund_data.basic_info.fund_name} ({fund_data.basic_info.fund_code})",
            "",
            f"**综合评分:** {score.score}/100 | **评级:** {score.rating_emoji} {score.rating}",
            "",
            "### 业绩表现",
            format_performance_text(score.performance),
            "",
            "### 风险指标",
            format_risk_text(score.risk),
        ]

        if fund_data.top_holdings:
            lines.append("")
            lines.append("### 前十大重仓股")
            lines.append(_format_holdings(fund_data.top_holdings))

        if fund_data.manager_info:
            lines.append("")
            lines.append("### 基金经理")
            lines.append(_format_manager(fund_data.manager_info))

        return "\n".join(lines)

    def generate_daily_summary(self, all_scores: list[FundScoreResult]) -> str:
        """生成每日汇总报告"""
        today = date.today().strftime("%Y-%m-%d")
        recommend_count = sum(1 for s in all_scores if s.rating == "推荐")
        watch_count = sum(1 for s in all_scores if s.rating == "观望")
        caution_count = sum(1 for s in all_scores if s.rating == "谨慎")

        lines = [
            f"🎯 {today} 基金分析报告",
            f"共分析{len(all_scores)}只基金 | 🟢推荐:{recommend_count} 🟡观望:{watch_count} 🔴谨慎:{caution_count}",
            "",
            "📊 分析结果摘要",
        ]

        for score in all_scores:
            lines.append(
                f"{score.rating_emoji} {score.fund_name}({score.fund_code}): "
                f"{score.rating} | 评分 {score.score} | {score.summary}"
            )

        return "\n".join(lines)
