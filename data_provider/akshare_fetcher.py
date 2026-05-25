"""akshare 数据源实现 - 封装东方财富基金数据接口"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd

from data_provider.base import BaseFundFetcher
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

logger = logging.getLogger(__name__)

# 请求间隔(秒)，避免触发反爬
REQUEST_INTERVAL = 0.5


def _safe_float(val, default=None) -> Optional[float]:
    """安全转换为 float"""
    if val is None or pd.isna(val):
        return default
    try:
        if isinstance(val, str):
            val = val.replace("%", "").replace(",", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=None) -> Optional[int]:
    """安全转换为 int"""
    if val is None or pd.isna(val):
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _parse_date(val) -> Optional[date]:
    """解析日期"""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    try:
        val = str(val).strip()
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _throttle():
    """请求限速"""
    time.sleep(REQUEST_INTERVAL)


class AkshareFetcher(BaseFundFetcher):
    """基于 akshare 的基金数据获取器"""

    def get_fund_basic_info(self, fund_code: str) -> Optional[FundBasicInfo]:
        """获取基金基础信息"""
        try:
            _throttle()
            # 尝试从雪球获取基础信息
            df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if df is not None and not df.empty:
                info_dict = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
                # 解析基金规模 (去掉"亿"等单位)
                size_str = str(info_dict.get("最新规模", ""))
                size_val = _safe_float(size_str.replace("亿", "").replace(",", ""))

                return FundBasicInfo(
                    fund_code=fund_code,
                    fund_name=str(info_dict.get("基金名称", info_dict.get("基金全称", f"基金{fund_code}"))),
                    fund_type=str(info_dict.get("基金类型", "")),
                    establish_date=_parse_date(info_dict.get("成立时间")),
                    fund_size=size_val,
                    manager_name=str(info_dict.get("基金经理", "")),
                    custodian=str(info_dict.get("托管银行", "")),
                )
        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 基础信息失败(雪球): {e}")

        # 降级: 尝试从基金列表获取名称
        try:
            _throttle()
            df = ak.fund_name_em()
            if df is not None and not df.empty:
                match = df[df["基金代码"] == fund_code]
                if not match.empty:
                    row = match.iloc[0]
                    return FundBasicInfo(
                        fund_code=fund_code,
                        fund_name=str(row.get("基金简称", f"基金{fund_code}")),
                        fund_type=str(row.get("基金类型", "")),
                    )
        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 基础信息失败(列表): {e}")

        # 最终降级: 返回基本信息
        return FundBasicInfo(fund_code=fund_code, fund_name=f"基金{fund_code}")

    def get_nav_history(self, fund_code: str, days: int = 365) -> list[NavRecord]:
        """获取基金净值历史"""
        try:
            _throttle()
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if df is None or df.empty:
                logger.warning(f"基金 {fund_code} 净值数据为空")
                return []

            records = []
            cutoff = date.today() - timedelta(days=days)

            for _, row in df.iterrows():
                nav_date = _parse_date(row.get("净值日期"))
                if nav_date is None:
                    continue
                if nav_date < cutoff:
                    continue

                records.append(NavRecord(
                    date=nav_date,
                    nav=_safe_float(row.get("单位净值"), 0.0),
                    acc_nav=_safe_float(row.get("累计净值"), 0.0),
                    day_growth=_safe_float(str(row.get("日增长率", "0")).replace("%", ""), 0.0),
                ))

            # 按日期升序
            records.sort(key=lambda r: r.date)
            logger.info(f"基金 {fund_code} 获取到 {len(records)} 条净值记录")
            return records

        except Exception as e:
            logger.error(f"获取基金 {fund_code} 净值历史失败: {e}")
            return []

    def get_top_holdings(self, fund_code: str) -> list[HoldingStock]:
        """获取前十大重仓股"""
        try:
            _throttle()
            # 使用最近的报告期
            current_year = date.today().year
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=str(current_year))

            if df is None or df.empty:
                # 尝试上一年
                _throttle()
                df = ak.fund_portfolio_hold_em(symbol=fund_code, date=str(current_year - 1))

            if df is None or df.empty:
                return []

            holdings = []
            for idx, (_, row) in enumerate(df.iterrows()):
                if idx >= 10:
                    break
                stock_code = str(row.get("股票代码", ""))
                stock_name = str(row.get("股票名称", ""))
                ratio = _safe_float(row.get("占净值比例"), 0.0)
                holdings.append(HoldingStock(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    ratio=ratio,
                    rank=idx + 1,
                ))

            logger.info(f"基金 {fund_code} 获取到 {len(holdings)} 条重仓股")
            return holdings

        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 持仓失败: {e}")
            return []

    def get_industry_allocation(self, fund_code: str) -> list[IndustryAllocation]:
        """获取行业配置"""
        try:
            _throttle()
            current_year = date.today().year
            df = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, date=str(current_year))

            if df is None or df.empty:
                _throttle()
                df = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, date=str(current_year - 1))

            if df is None or df.empty:
                return []

            allocations = []
            for _, row in df.iterrows():
                industry = str(row.get("行业", row.iloc[0] if len(row) > 0 else ""))
                ratio = _safe_float(row.get("占净值比例", row.iloc[1] if len(row) > 1 else None), 0.0)
                if industry:
                    allocations.append(IndustryAllocation(industry=industry, ratio=ratio))

            logger.info(f"基金 {fund_code} 获取到 {len(allocations)} 条行业配置")
            return allocations

        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 行业配置失败: {e}")
            return []

    def get_manager_info(self, fund_code: str) -> Optional[ManagerInfo]:
        """获取基金经理信息"""
        try:
            _throttle()
            # 先获取基金基础信息中的经理名称
            basic = self.get_fund_basic_info(fund_code)
            if not basic or not basic.manager_name:
                return None

            manager_name = basic.manager_name

            # 尝试获取经理信息
            _throttle()
            try:
                df = ak.fund_manager_em()
                if df is not None and not df.empty:
                    # 找到当前经理的记录
                    match = df[df["姓名"] == manager_name]
                    if not match.empty:
                        row = match.iloc[0]
                        return ManagerInfo(
                            name=manager_name,
                            fund_size=_safe_float(row.get("现任基金资产总规模")),
                            total_return=_safe_float(row.get("现任基金最佳回报")),
                            fund_count=1,
                        )
            except Exception:
                pass

            return ManagerInfo(name=manager_name)

        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 经理信息失败: {e}")
            return None

    def get_fund_fee(self, fund_code: str) -> Optional[FundFee]:
        """获取基金费率"""
        try:
            _throttle()
            # 从雪球获取费率信息
            df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if df is not None and not df.empty:
                info_dict = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
                return FundFee(
                    management_fee=_safe_float(info_dict.get("管理费", info_dict.get("管理费率"))),
                    custody_fee=_safe_float(info_dict.get("托管费", info_dict.get("托管费率"))),
                    sales_service_fee=_safe_float(info_dict.get("销售服务费", info_dict.get("销售服务费率"))),
                    purchase_fee=_safe_float(info_dict.get("申购费", info_dict.get("申购费率"))),
                    redemption_fee=_safe_float(info_dict.get("赎回费", info_dict.get("赎回费率"))),
                )
        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 费率失败: {e}")

        return None

    def get_fund_ranking(self, fund_code: str) -> Optional[FundRanking]:
        """获取基金排名"""
        try:
            # 先确定基金类型
            basic = self.get_fund_basic_info(fund_code)
            fund_type = basic.fund_type if basic else ""

            # 根据类型选择排名接口
            _throttle()
            rank_type = "全部"
            if "股票" in fund_type:
                rank_type = "股票型"
            elif "混合" in fund_type:
                rank_type = "混合型"
            elif "债券" in fund_type:
                rank_type = "债券型"
            elif "指数" in fund_type or "ETF" in fund_type:
                rank_type = "指数型"

            df = ak.fund_open_fund_rank_em(symbol=rank_type)
            if df is None or df.empty:
                return None

            # 找到目标基金
            match = df[df["基金代码"] == fund_code]
            if match.empty:
                return None

            row = match.iloc[0]
            total = len(df)

            # 计算近1年排名百分位
            rank_col = None
            for col in ["近1年", "近1年收益率"]:
                if col in df.columns:
                    rank_col = col
                    break

            if rank_col:
                # 按近1年收益排序，计算排名
                df_sorted = df.dropna(subset=[rank_col]).sort_values(rank_col, ascending=False)
                rank_pos = df_sorted.index.get_loc(row.name) + 1 if row.name in df_sorted.index else None
                total_sorted = len(df_sorted)
                percentile = (rank_pos / total_sorted * 100) if rank_pos else None

                return FundRanking(
                    rank=rank_pos,
                    total=total_sorted,
                    percentile=round(percentile, 1) if percentile else None,
                )

            return FundRanking(total=total)

        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 排名失败: {e}")
            return None

    def get_realtime_estimation(self, fund_code: str) -> Optional[FundEstimation]:
        """获取实时估值"""
        try:
            _throttle()
            df = ak.fund_value_estimation_em(symbol="开放式基金")
            if df is None or df.empty:
                return None

            match = df[df["基金代码"] == fund_code]
            if match.empty:
                return None

            row = match.iloc[0]
            return FundEstimation(
                estimated_nav=_safe_float(row.get("估算值")),
                estimated_growth=_safe_float(str(row.get("估算涨幅", "0")).replace("%", "")),
                estimation_time=datetime.now(),
            )

        except Exception as e:
            logger.warning(f"获取基金 {fund_code} 实时估值失败: {e}")
            return None
