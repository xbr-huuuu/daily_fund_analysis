"""基金数据模型定义 - 所有模块共享的数据结构"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class FundBasicInfo(BaseModel):
    """基金基础信息"""
    fund_code: str = Field(description="基金代码, e.g. '161725'")
    fund_name: str = Field(description="基金名称")
    fund_type: str = Field(default="", description="基金类型: 股票型/混合型/债券型/指数型")
    nav: Optional[float] = Field(default=None, description="最新单位净值")
    acc_nav: Optional[float] = Field(default=None, description="累计净值")
    nav_date: Optional[date] = Field(default=None, description="净值日期")
    day_growth: Optional[float] = Field(default=None, description="日涨跌幅(%)")
    establish_date: Optional[date] = Field(default=None, description="成立日期")
    fund_size: Optional[float] = Field(default=None, description="基金规模(亿元)")
    manager_name: Optional[str] = Field(default=None, description="基金经理")
    custodian: Optional[str] = Field(default=None, description="托管人")


class NavRecord(BaseModel):
    """单条净值记录"""
    date: date
    nav: float = Field(description="单位净值")
    acc_nav: float = Field(description="累计净值")
    day_growth: float = Field(description="日涨跌幅(%)")


class HoldingStock(BaseModel):
    """重仓股持仓"""
    stock_code: str
    stock_name: str
    ratio: float = Field(description="占净值比例(%)")
    rank: int = Field(description="持仓排名 1-10")


class IndustryAllocation(BaseModel):
    """行业配置"""
    industry: str
    ratio: float = Field(description="占净值比例(%)")


class ManagerInfo(BaseModel):
    """基金经理信息"""
    name: str
    tenure_start: Optional[date] = Field(default=None, description="任职日期")
    fund_size: Optional[float] = Field(default=None, description="管理规模(亿元)")
    total_return: Optional[float] = Field(default=None, description="任职回报(%)")
    annualized_return: Optional[float] = Field(default=None, description="年化回报(%)")
    max_drawdown: Optional[float] = Field(default=None, description="最大回撤(%)")
    fund_count: int = Field(default=0, description="管理基金数量")


class FundFee(BaseModel):
    """费率结构"""
    management_fee: Optional[float] = Field(default=None, description="管理费(%)")
    custody_fee: Optional[float] = Field(default=None, description="托管费(%)")
    sales_service_fee: Optional[float] = Field(default=None, description="销售服务费(%)")
    purchase_fee: Optional[float] = Field(default=None, description="申购费(%)")
    redemption_fee: Optional[float] = Field(default=None, description="赎回费(%)")


class FundRanking(BaseModel):
    """基金排名"""
    rank: Optional[int] = Field(default=None, description="同类排名")
    total: Optional[int] = Field(default=None, description="同类基金总数")
    percentile: Optional[float] = Field(default=None, description="百分位 (0-100, 越小越好)")


class FundEstimation(BaseModel):
    """实时估值"""
    estimated_nav: Optional[float] = Field(default=None, description="估算净值")
    estimated_growth: Optional[float] = Field(default=None, description="估算涨跌幅(%)")
    estimation_time: Optional[datetime] = Field(default=None, description="估值时间")


class FundFullData(BaseModel):
    """基金完整数据 - 聚合所有维度"""
    basic_info: FundBasicInfo
    nav_history: list[NavRecord] = Field(default_factory=list)
    top_holdings: list[HoldingStock] = Field(default_factory=list)
    industry_allocation: list[IndustryAllocation] = Field(default_factory=list)
    manager_info: Optional[ManagerInfo] = None
    fee: Optional[FundFee] = None
    ranking: Optional[FundRanking] = None
    estimation: Optional[FundEstimation] = None
    fetch_errors: dict[str, str] = Field(default_factory=dict, description="记录哪些接口失败")
