"""
FastAPI 主应用
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api import translate, system
from app.database import engine, Base
import os

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时创建表；MySQL 不可用时仅打日志，不阻止服务启动"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ready.")
    except OperationalError as e:
        logger.warning(
            "Database unavailable at startup (tables not created): %s. "
            "Check .env: DATABASE_URL (MySQL user/password) and that MySQL is running.",
            e,
        )
    yield
    # shutdown: engine.dispose() 可选
    engine.dispose()


# 创建 FastAPI 应用
app = FastAPI(
    title="AI Translator API",
    description="智能翻译服务 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置：本地开发同时允许 localhost 与 127.0.0.1，避免跨域
_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
_env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
allowed_origins = _env_origins if _env_origins else _default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 注册路由
app.include_router(translate.router)
app.include_router(system.router)


@app.get("/")
async def root():
    return {
        "message": "AI Translator API",
        "version": "1.0.0",
        "docs": "/docs"
    }
