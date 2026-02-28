"""
FastAPI 主应用
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import translate, system, literary_translation
from app.database import engine, Base
import os

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title="AI Translator API",
    description="智能翻译服务 API",
    version="1.0.0"
)

# CORS 配置
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(translate.router)
app.include_router(system.router)
app.include_router(literary_translation.router)


@app.get("/")
async def root():
    return {
        "message": "AI Translator API",
        "version": "1.0.0",
        "docs": "/docs"
    }
