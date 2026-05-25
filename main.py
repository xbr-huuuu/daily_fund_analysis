"""基金智能分析系统 - CLI 入口"""

import asyncio
import logging
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

import click

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings
from data_provider.akshare_fetcher import AkshareFetcher
from data_provider.manager import DataProviderManager
from analysis_engine.metrics import calculate_performance_metrics, calculate_risk_metrics, calculate_comprehensive_score
from analysis_engine.scorer import FundScoreResult
from analysis_engine.report_generator import ReportGenerator
from dca_calculator.calculator import calculate_dca_advice, format_dca_report
from notification.sender import NotificationManager
from storage.database import init_db
from storage.repository import FundRepository

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """支付宝基金智能分析系统"""
    pass


@cli.command()
@click.option("--funds", default=None, help="基金代码列表，逗号分隔 (覆盖 .env 配置)")
@click.option("--dry-run", is_flag=True, help="仅获取数据和计算指标，不调用 LLM 和推送")
def run(funds: str, dry_run: bool):
    """执行每日基金分析"""
    config = Settings()

    if funds:
        config.fund_codes = funds

    fund_codes = config.get_fund_code_list()
    if not fund_codes:
        click.echo("❌ 请配置基金代码: 设置环境变量 DFA_FUND_CODES 或使用 --funds 参数")
        click.echo("   示例: python main.py run --funds 161725,110011,005827")
        sys.exit(1)

    click.echo(f"📊 开始分析 {len(fund_codes)} 只基金: {', '.join(fund_codes)}")
    asyncio.run(_run_analysis(fund_codes, config, dry_run))


async def _run_analysis(fund_codes: list[str], config: Settings, dry_run: bool):
    """执行分析流程"""
    # 初始化组件
    session_factory = init_db(config.database_url)
    repo = FundRepository(session_factory())
    provider = DataProviderManager(AkshareFetcher())
    report_gen = ReportGenerator(config) if not dry_run else None
    notifier = NotificationManager.from_config(config) if not dry_run else None

    all_scores: list[FundScoreResult] = []
    all_reports: list[str] = []
    all_dca: list = []
    holding_map = config.get_holding_map()

    for code in fund_codes:
        click.echo(f"\n{'='*50}")
        click.echo(f"🔍 正在分析基金: {code}")

        try:
            # 1. 获取数据
            click.echo("  📥 获取数据...")
            fund_data = provider.get_fund_full_data(code)
            click.echo(f"  ✅ 基金名称: {fund_data.basic_info.fund_name}")

            if fund_data.fetch_errors:
                click.echo(f"  ⚠️  部分数据获取失败: {list(fund_data.fetch_errors.keys())}")

            if not fund_data.nav_history:
                click.echo(f"  ❌ 无净值数据，跳过")
                continue

            click.echo(f"  📈 净值记录: {len(fund_data.nav_history)} 条")

            # 2. 计算指标
            click.echo("  📊 计算指标...")
            perf = calculate_performance_metrics(fund_data.nav_history)
            risk = calculate_risk_metrics(fund_data.nav_history, config.risk_free_rate)
            score, rating = calculate_comprehensive_score(
                perf, risk, fund_data.ranking, fund_data.manager_info, fund_data.fee
            )

            score_result = FundScoreResult.create(
                fund_code=code,
                fund_name=fund_data.basic_info.fund_name,
                score=score,
                rating=rating,
                performance=perf,
                risk=risk,
            )
            all_scores.append(score_result)

            click.echo(f"  📊 综合评分: {score}/100 | 评级: {score_result.rating_emoji} {rating}")

            # 2.5 智能定投建议
            dca_advice = None
            if not dry_run and risk.max_drawdown is not None:
                held = holding_map.get(code, 0)
                remaining = config.fund_budget - held
                if remaining > 0:
                    dca_advice = calculate_dca_advice(
                        fund_code=code,
                        fund_name=fund_data.basic_info.fund_name,
                        current_drawdown=risk.max_drawdown,
                        remaining_budget=remaining,
                        plan_months=config.dca_plan_months,
                    )
                    all_dca.append(dca_advice)
                    click.echo(f"  💡 定投建议: {dca_advice.suggested_amount:.2f}元 ({dca_advice.trend_emoji} {dca_advice.multiplier}x)")

            # 3. 生成报告
            if not dry_run and report_gen:
                click.echo("  🤖 生成 AI 报告...")
                report_text = report_gen.generate_single_report(fund_data, score_result)
                all_reports.append(report_text)
            else:
                report_text = f"评分: {score}/100 | 评级: {rating}"
                all_reports.append(report_text)

            # 4. 保存到数据库
            click.echo("  💾 保存数据...")
            repo.save_fund(code, fund_data.basic_info.fund_name, fund_data.basic_info.fund_type)
            if fund_data.nav_history:
                repo.save_nav_history(code, fund_data.nav_history)
            repo.save_analysis_report(
                fund_code=code,
                score=score,
                rating=rating,
                summary=score_result.summary,
                full_report=report_text,
                metrics=asdict(perf),
            )
            if fund_data.top_holdings:
                repo.save_holdings(code, fund_data.top_holdings)

            # 5. 检查经理变动
            if fund_data.manager_info and fund_data.manager_info.name:
                if repo.check_manager_change(code, fund_data.manager_info.name):
                    click.echo(f"  ⚠️  检测到基金经理变动!")

            click.echo(f"  ✅ 分析完成")

        except Exception as e:
            logger.error(f"分析基金 {code} 失败: {e}", exc_info=True)
            click.echo(f"  ❌ 分析失败: {e}")

    # 6. 生成汇总报告
    if all_scores:
        click.echo(f"\n{'='*50}")
        click.echo("📊 生成汇总报告...")

        if report_gen:
            summary = report_gen.generate_daily_summary(all_scores)
        else:
            summary = _format_simple_summary(all_scores)

        # 追加定投建议
        if all_dca:
            summary += "\n\n### 💡 智能定投建议\n\n"
            for d in all_dca:
                summary += format_dca_report(d) + "\n"

        click.echo("\n" + summary)

        # 7. 推送通知
        if not dry_run and notifier and notifier.notifiers:
            click.echo("\n📤 推送通知...")
            results = await notifier.broadcast(
                f"📊 基金分析报告 ({date.today()})",
                summary,
            )
            for channel, success in results.items():
                status = "✅" if success else "❌"
                click.echo(f"  {status} {channel}")
        elif not dry_run:
            click.echo("\n⚠️  未配置通知渠道，跳过推送")

    click.echo(f"\n{'='*50}")
    click.echo("🎉 分析完成!")


def _format_simple_summary(scores: list[FundScoreResult]) -> str:
    """简单汇总报告"""
    today = date.today().strftime("%Y-%m-%d")
    recommend = sum(1 for s in scores if s.rating == "推荐")
    watch = sum(1 for s in scores if s.rating == "观望")
    caution = sum(1 for s in scores if s.rating == "谨慎")

    lines = [
        f"🎯 {today} 基金分析报告",
        f"共分析{len(scores)}只基金 | 🟢推荐:{recommend} 🟡观望:{watch} 🔴谨慎:{caution}",
        "",
        "📊 分析结果摘要",
    ]

    for s in scores:
        lines.append(f"{s.rating_emoji} {s.fund_name}({s.fund_code}): {s.rating} | 评分 {s.score} | {s.summary}")

    return "\n".join(lines)


@cli.command()
@click.argument("fund_code")
def info(fund_code: str):
    """查看基金信息"""
    click.echo(f"🔍 查询基金: {fund_code}")

    provider = DataProviderManager(AkshareFetcher())
    fund_data = provider.get_fund_full_data(fund_code)

    click.echo(f"\n基金名称: {fund_data.basic_info.fund_name}")
    click.echo(f"基金类型: {fund_data.basic_info.fund_type}")
    click.echo(f"基金代码: {fund_data.basic_info.fund_code}")

    if fund_data.basic_info.nav:
        click.echo(f"最新净值: {fund_data.basic_info.nav}")
    if fund_data.basic_info.manager_name:
        click.echo(f"基金经理: {fund_data.basic_info.manager_name}")

    if fund_data.nav_history:
        click.echo(f"\n净值记录: {len(fund_data.nav_history)} 条")
        click.echo(f"  最新日期: {fund_data.nav_history[-1].date}")
        click.echo(f"  最新净值: {fund_data.nav_history[-1].nav}")

    if fund_data.top_holdings:
        click.echo(f"\n前十大重仓股:")
        for h in fund_data.top_holdings[:10]:
            click.echo(f"  {h.rank}. {h.stock_name}({h.stock_code}): {h.ratio:.2f}%")

    if fund_data.fetch_errors:
        click.echo(f"\n⚠️  获取失败的接口: {list(fund_data.fetch_errors.keys())}")


@cli.command()
@click.argument("fund_code")
def history(fund_code: str):
    """查看历史分析报告"""
    config = Settings()
    db_session = init_db(config.database_url)
    repo = FundRepository(db_session)

    reports = repo.get_report_history(fund_code, limit=10)
    if not reports:
        click.echo(f"未找到基金 {fund_code} 的历史报告")
        return

    click.echo(f"📊 基金 {fund_code} 历史报告 (最近{len(reports)}条):\n")
    for report in reports:
        emoji = {"推荐": "🟢", "观望": "🟡", "谨慎": "🔴"}.get(report.rating, "⚪")
        click.echo(
            f"  {report.analysis_date} | {emoji} {report.rating} | "
            f"评分 {report.score} | {report.summary}"
        )


@cli.command()
def test():
    """测试系统是否正常工作"""
    click.echo("🧪 系统测试...")

    # 测试配置
    config = Settings()
    click.echo(f"✅ 配置加载成功")

    # 测试数据源
    fetcher = AkshareFetcher()
    click.echo("✅ 数据源初始化成功")

    # 测试获取基金列表
    try:
        import akshare as ak
        df = ak.fund_name_em()
        click.echo(f"✅ 基金列表获取成功: {len(df)} 只基金")
    except Exception as e:
        click.echo(f"❌ 基金列表获取失败: {e}")

    # 测试通知渠道
    notifier = NotificationManager.from_config(config)
    if notifier.notifiers:
        click.echo(f"✅ 通知渠道: {len(notifier.notifiers)} 个")
    else:
        click.echo("⚠️  未配置通知渠道")

    click.echo("\n🎉 测试完成!")


if __name__ == "__main__":
    cli()
