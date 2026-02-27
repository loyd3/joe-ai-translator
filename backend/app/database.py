"""
数据库配置
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.core.ai_client import get_settings
import os

settings = get_settings()

# 创建数据库引擎
DATABASE_URL = settings.database_url if hasattr(settings, 'database_url') else os.getenv(
    "DATABASE_URL", "sqlite:///./translator.db"
)

# SQLite 特殊配置
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # MySQL/PostgreSQL 配置
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
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
