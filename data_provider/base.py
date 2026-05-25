"""数据源抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional

from data_provider.models import (
    FundBasicInfo,
    FundEstimation,
    FundFee,
    FundRanking,
    HoldingStock,
    IndustryAllocation,
    ManagerInfo,
    NavRecord,
)


class BaseFundFetcher(ABC):
    """基金数据获取器抽象基类"""

    @abstractmethod
    def get_fund_basic_info(self, fund_code: str) -> Optional[FundBasicInfo]:
        """获取基金基础信息"""
        ...

    @abstractmethod
    def get_nav_history(self, fund_code: str, days: int = 365) -> list[NavRecord]:
        """获取基金净值历史"""
        ...

    @abstractmethod
    def get_top_holdings(self, fund_code: str) -> list[HoldingStock]:
        """获取前十大重仓股"""
        ...

    @abstractmethod
    def get_industry_allocation(self, fund_code: str) -> list[IndustryAllocation]:
        """获取行业配置"""
        ...

    @abstractmethod
    def get_manager_info(self, fund_code: str) -> Optional[ManagerInfo]:
        """获取基金经理信息"""
        ...

    @abstractmethod
    def get_fund_fee(self, fund_code: str) -> Optional[FundFee]:
        """获取基金费率"""
        ...

    @abstractmethod
    def get_fund_ranking(self, fund_code: str) -> Optional[FundRanking]:
        """获取基金排名"""
        ...

    @abstractmethod
    def get_realtime_estimation(self, fund_code: str) -> Optional[FundEstimation]:
        """获取实时估值"""
        ...
