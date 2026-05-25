"""数据访问层 - CRUD 操作封装"""

import json
import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from storage.models import AnalysisReport, Fund, FundHolding, ManagerTracking, NavHistory

logger = logging.getLogger(__name__)


class FundRepository:
    """基金数据仓库"""

    def __init__(self, session: Session):
        self.session = session

    def save_fund(self, fund_code: str, fund_name: str, fund_type: str = "") -> Fund:
        """保存或更新基金基础信息"""
        fund = self.session.query(Fund).filter_by(fund_code=fund_code).first()
        if fund:
            fund.fund_name = fund_name
            fund.fund_type = fund_type
        else:
            fund = Fund(fund_code=fund_code, fund_name=fund_name, fund_type=fund_type)
            self.session.add(fund)
        self.session.commit()
        return fund

    def save_nav_history(self, fund_code: str, records: list) -> int:
        """保存净值历史，返回新增记录数"""
        added = 0
        for record in records:
            exists = (
                self.session.query(NavHistory)
                .filter_by(fund_code=fund_code, date=record.date)
                .first()
            )
            if not exists:
                nav = NavHistory(
                    fund_code=fund_code,
                    date=record.date,
                    nav=record.nav,
                    acc_nav=record.acc_nav,
                    day_growth=record.day_growth,
                )
                self.session.add(nav)
                added += 1
        self.session.commit()
        return added

    def save_analysis_report(
        self,
        fund_code: str,
        score: int,
        rating: str,
        summary: str,
        full_report: str,
        metrics: Optional[dict] = None,
    ) -> AnalysisReport:
        """保存分析报告"""
        report = AnalysisReport(
            fund_code=fund_code,
            analysis_date=date.today(),
            score=score,
            rating=rating,
            summary=summary,
            full_report=full_report,
            metrics_json=json.dumps(metrics) if metrics else None,
        )
        self.session.add(report)
        self.session.commit()
        return report

    def get_latest_report(self, fund_code: str) -> Optional[AnalysisReport]:
        """获取最新分析报告"""
        return (
            self.session.query(AnalysisReport)
            .filter_by(fund_code=fund_code)
            .order_by(AnalysisReport.analysis_date.desc())
            .first()
        )

    def get_report_history(self, fund_code: str, limit: int = 30) -> list[AnalysisReport]:
        """获取历史报告"""
        return (
            self.session.query(AnalysisReport)
            .filter_by(fund_code=fund_code)
            .order_by(AnalysisReport.analysis_date.desc())
            .limit(limit)
            .all()
        )

    def save_holdings(self, fund_code: str, holdings: list) -> None:
        """保存持仓数据"""
        for h in holdings:
            holding = FundHolding(
                fund_code=fund_code,
                report_date=date.today().strftime("%Y-%m-%d"),
                stock_code=h.stock_code,
                stock_name=h.stock_name,
                ratio=h.ratio,
                rank=h.rank,
            )
            self.session.add(holding)
        self.session.commit()

    def check_manager_change(self, fund_code: str, current_manager: str) -> bool:
        """检查基金经理是否变动，返回是否变动"""
        last_tracking = (
            self.session.query(ManagerTracking)
            .filter_by(fund_code=fund_code, is_active=True)
            .order_by(ManagerTracking.detected_at.desc())
            .first()
        )

        if last_tracking is None:
            # 首次记录
            tracking = ManagerTracking(
                fund_code=fund_code,
                manager_name=current_manager,
                is_active=True,
            )
            self.session.add(tracking)
            self.session.commit()
            return False

        if last_tracking.manager_name != current_manager:
            # 经理变动
            last_tracking.is_active = False
            new_tracking = ManagerTracking(
                fund_code=fund_code,
                manager_name=current_manager,
                is_active=True,
            )
            self.session.add(new_tracking)
            self.session.commit()
            logger.warning(f"基金 {fund_code} 经理变动: {last_tracking.manager_name} -> {current_manager}")
            return True

        return False

    def close(self):
        """关闭会话"""
        self.session.close()
