"""数据库初始化"""

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def init_db(database_url: str = "sqlite:///data/fund_analysis.db") -> sessionmaker:
    """初始化数据库，返回 Session 工厂"""
    global _engine, _SessionLocal

    if _SessionLocal is not None:
        return _SessionLocal

    # 确保数据目录存在
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(database_url, echo=False)
    _SessionLocal = sessionmaker(bind=_engine)

    # 创建表
    from storage.models import Base
    Base.metadata.create_all(_engine)
    logger.info(f"数据库初始化完成: {database_url}")

    return _SessionLocal


def get_session() -> Session:
    """获取数据库会话"""
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()
