"""数据源管理器 - 聚合单只基金的全部数据"""

import logging
from typing import Optional

from data_provider.base import BaseFundFetcher
from data_provider.models import FundFullData

logger = logging.getLogger(__name__)


class DataProviderManager:
    """数据源管理器，负责获取单只基金的完整数据"""

    def __init__(self, fetcher: BaseFundFetcher):
        self.fetcher = fetcher

    def get_fund_full_data(self, fund_code: str) -> FundFullData:
        """一次性获取某只基金的全部数据，单个接口失败不影响其他接口"""
        errors: dict[str, str] = {}

        # 基础信息 (必须)
        basic_info = self.fetcher.get_fund_basic_info(fund_code)
        if basic_info is None:
            from data_provider.models import FundBasicInfo
            basic_info = FundBasicInfo(fund_code=fund_code, fund_name=f"基金{fund_code}")
            errors["basic_info"] = "获取失败"

        # 净值历史 (关键)
        nav_history = []
        try:
            nav_history = self.fetcher.get_nav_history(fund_code)
        except Exception as e:
            errors["nav_history"] = str(e)
            logger.error(f"获取 {fund_code} 净值历史异常: {e}")

        # 重仓股
        top_holdings = []
        try:
            top_holdings = self.fetcher.get_top_holdings(fund_code)
        except Exception as e:
            errors["top_holdings"] = str(e)

        # 行业配置
        industry_allocation = []
        try:
            industry_allocation = self.fetcher.get_industry_allocation(fund_code)
        except Exception as e:
            errors["industry_allocation"] = str(e)

        # 基金经理
        manager_info = None
        try:
            manager_info = self.fetcher.get_manager_info(fund_code)
        except Exception as e:
            errors["manager_info"] = str(e)

        # 费率
        fee = None
        try:
            fee = self.fetcher.get_fund_fee(fund_code)
        except Exception as e:
            errors["fee"] = str(e)

        # 排名
        ranking = None
        try:
            ranking = self.fetcher.get_fund_ranking(fund_code)
        except Exception as e:
            errors["ranking"] = str(e)

        # 实时估值
        estimation = None
        try:
            estimation = self.fetcher.get_realtime_estimation(fund_code)
        except Exception as e:
            errors["estimation"] = str(e)

        if errors:
            logger.warning(f"基金 {fund_code} 部分数据获取失败: {list(errors.keys())}")

        return FundFullData(
            basic_info=basic_info,
            nav_history=nav_history,
            top_holdings=top_holdings,
            industry_allocation=industry_allocation,
            manager_info=manager_info,
            fee=fee,
            ranking=ranking,
            estimation=estimation,
            fetch_errors=errors,
        )
