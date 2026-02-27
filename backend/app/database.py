"""
数据库配置 - MySQL 主配置
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.core.ai_client import get_settings
import os

settings = get_settings()

# 获取数据库 URL，默认使用 MySQL
DATABASE_URL = settings.database_url

# MySQL 连接配置
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,  # 自动检测断开的连接
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """初始化数据库 - 创建所有表"""
    Base.metadata.create_all(bind=engine)
