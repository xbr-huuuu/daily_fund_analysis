"""SQLAlchemy ORM 模型"""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text, Boolean, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Fund(Base):
    """基金基础信息表"""
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(20), unique=True, index=True, nullable=False)
    fund_name = Column(String(200))
    fund_type = Column(String(50))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class NavHistory(Base):
    """净值历史表"""
    __tablename__ = "nav_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(20), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    nav = Column(Float)
    acc_nav = Column(Float)
    day_growth = Column(Float)


class AnalysisReport(Base):
    """分析报告表"""
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(20), index=True, nullable=False)
    analysis_date = Column(Date, index=True, nullable=False)
    score = Column(Integer)
    rating = Column(String(20))
    summary = Column(Text)
    full_report = Column(Text)
    metrics_json = Column(Text)
    created_at = Column(DateTime, default=func.now())


class FundHolding(Base):
    """基金持仓表"""
    __tablename__ = "fund_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(20), index=True, nullable=False)
    report_date = Column(String(20))
    stock_code = Column(String(20))
    stock_name = Column(String(100))
    ratio = Column(Float)
    rank = Column(Integer)


class ManagerTracking(Base):
    """基金经理变动追踪表"""
    __tablename__ = "manager_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(20), index=True, nullable=False)
    manager_name = Column(String(100))
    detected_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
