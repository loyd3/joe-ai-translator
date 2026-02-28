"""
数据库配置 - 支持 MySQL 和 SQLite
"""

import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.ai_client import get_settings

settings = get_settings()


def _build_mysql_url() -> str | None:
    """若在 .env 中设置了 MYSQL_USER / MYSQL_PASSWORD（已由 Settings 加载），则用其构建 URL"""
    user = getattr(settings, "mysql_user", None) or os.getenv("MYSQL_USER")
    password = getattr(settings, "mysql_password", None)
    if password is None:
        password = os.getenv("MYSQL_PASSWORD")
    if not user or password is None:  # 允许空字符串密码
        return None
    host = getattr(settings, "mysql_host", None) or os.getenv("MYSQL_HOST") or "localhost"
    port = getattr(settings, "mysql_port", None) or os.getenv("MYSQL_PORT") or "3306"
    database = getattr(settings, "mysql_database", None) or os.getenv("MYSQL_DATABASE") or "aitranslator"
    user_enc = quote_plus(str(user))
    password_enc = quote_plus(str(password))
    return f"mysql+pymysql://{user_enc}:{password_enc}@{host}:{port}/{database}?charset=utf8mb4"


# 优先使用 MYSQL_*（来自 .env，由 Settings 加载），否则用 settings.database_url
DATABASE_URL = _build_mysql_url() or settings.database_url

# 判断数据库类型并创建相应的引擎
if DATABASE_URL.startswith('sqlite'):
    # SQLite 配置（开发环境）
    # 确保目录存在
    db_path = DATABASE_URL.replace('sqlite:///', '')
    if db_path.startswith('./'):
        db_path = db_path[2:]
    if db_path and not db_path.startswith('/'):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    
    engine = create_engine(
        DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # MySQL 配置（生产环境）
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
