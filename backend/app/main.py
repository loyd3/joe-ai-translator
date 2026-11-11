"""
FastAPI 主应用
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api import translate, system, literary_translation, style_agents, domain_dictionaries
from app.database import engine, Base
from app.models import models as _models  # noqa: F401  注册表结构
import os

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时创建表；MySQL 不可用时仅打日志，不阻止服务启动"""
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_story_profile_column()
        _ensure_style_agent_schema()
        _ensure_group_name_column()
        _ensure_translation_collab_mode_column()
        _ensure_document_groups_table()
        _ensure_ai_config_columns()
        _ensure_domain_dictionary_schema()
        _ensure_step5_localization_schema()
        logger.info("Database tables ready.")
    except OperationalError as e:
        logger.warning(
            "MySQL 连接失败（未创建表）: %s。请检查：1) MySQL 服务已启动；"
            "2) .env 中用户名/密码正确；若密码含 #@ 等特殊字符，请用 MYSQL_USER/MYSQL_PASSWORD 分别配置，或对 DATABASE_URL 中密码做 URL 编码；"
            "3) 可尝试将 host 改为 127.0.0.1。",
            e,
        )
    yield
    # shutdown: engine.dispose() 可选
    engine.dispose()


def _ensure_story_profile_column():
    """已有库不会被 create_all 改表，缺列时补上故事档案字段。"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        if "literary_translations" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("literary_translations")}
        if "story_profile" in columns:
            return
        ddl = "ALTER TABLE literary_translations ADD COLUMN story_profile JSON NULL"
        if engine.dialect.name == "sqlite":
            ddl = "ALTER TABLE literary_translations ADD COLUMN story_profile TEXT"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Added literary_translations.story_profile")
    except Exception as e:
        logger.warning("Could not ensure story_profile column: %s", e)


def _ensure_style_agent_schema():
    """确保文风表存在，并为翻译任务补上 style_agent_id。"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if "writing_style_agents" not in tables:
            Base.metadata.tables["writing_style_agents"].create(bind=engine, checkfirst=True)
            logger.info("Created writing_style_agents table")
        if "literary_translations" not in tables:
            return
        columns = {column["name"] for column in inspector.get_columns("literary_translations")}
        if "style_agent_id" in columns:
            return
        ddl = "ALTER TABLE literary_translations ADD COLUMN style_agent_id INT NULL"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Added literary_translations.style_agent_id")
    except Exception as e:
        logger.warning("Could not ensure style agent schema: %s", e)


def _ensure_group_name_column():
    """已有库不会被 create_all 改表，缺列时补上分组字段。"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        if "literary_translations" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("literary_translations")}
        if "group_name" in columns:
            return
        ddl = "ALTER TABLE literary_translations ADD COLUMN group_name VARCHAR(200) NULL"
        if engine.dialect.name == "sqlite":
            ddl = "ALTER TABLE literary_translations ADD COLUMN group_name VARCHAR(200)"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Added literary_translations.group_name")
    except Exception as e:
        logger.warning("Could not ensure group_name column: %s", e)


def _ensure_translation_collab_mode_column():
    """为翻译任务补齐 collab_mode（按任务选择全线上/全本地/混合）。"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        if "literary_translations" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("literary_translations")}
        if "collab_mode" in columns:
            return
        ddl = "ALTER TABLE literary_translations ADD COLUMN collab_mode VARCHAR(20) NULL"
        if engine.dialect.name == "sqlite":
            ddl = "ALTER TABLE literary_translations ADD COLUMN collab_mode VARCHAR(20)"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Added literary_translations.collab_mode")
    except Exception as e:
        logger.warning("Could not ensure translation collab_mode column: %s", e)


def _ensure_document_groups_table():
    """确保自定义分组表存在，并同步已有 group_name。"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if "document_groups" not in tables:
            Base.metadata.tables["document_groups"].create(bind=engine, checkfirst=True)
            logger.info("Created document_groups table")
        if "literary_translations" not in tables:
            return
        columns = {column["name"] for column in inspector.get_columns("literary_translations")}
        if "group_name" not in columns:
            return
        with engine.begin() as conn:
            if engine.dialect.name == "sqlite":
                conn.execute(text(
                    "INSERT OR IGNORE INTO document_groups (name, sort_order) "
                    "SELECT DISTINCT TRIM(group_name), 0 FROM literary_translations "
                    "WHERE group_name IS NOT NULL AND TRIM(group_name) <> ''"
                ))
            else:
                conn.execute(text(
                    "INSERT IGNORE INTO document_groups (name, sort_order) "
                    "SELECT DISTINCT TRIM(group_name), 0 FROM literary_translations "
                    "WHERE group_name IS NOT NULL AND TRIM(group_name) <> ''"
                ))
    except Exception as e:
        logger.warning("Could not ensure document_groups table: %s", e)


def _ensure_ai_config_columns():
    """为 ai_config 补齐高级采样与超时字段。"""
    from sqlalchemy import inspect, text
    extras = {
        "top_p": ("FLOAT NULL", "REAL"),
        "frequency_penalty": ("FLOAT NULL", "REAL"),
        "presence_penalty": ("FLOAT NULL", "REAL"),
        "timeout_seconds": ("INT NULL", "INTEGER"),
        "collab_mode": ("VARCHAR(20) NULL", "VARCHAR(20)"),
        "draft_provider": ("VARCHAR(50) NULL", "VARCHAR(50)"),
        "draft_api_key": ("VARCHAR(500) NULL", "VARCHAR(500)"),
        "draft_model": ("VARCHAR(200) NULL", "VARCHAR(200)"),
        "draft_base_url": ("VARCHAR(500) NULL", "VARCHAR(500)"),
        "draft_fallback": ("TINYINT(1) NULL", "INTEGER"),
        "draft_think": ("TINYINT(1) NULL", "INTEGER"),
        "term_hit_table_max_entries": ("INT NULL", "INTEGER"),
    }
    try:
        inspector = inspect(engine)
        if "ai_config" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("ai_config")}
        dialect = engine.dialect.name
        with engine.begin() as conn:
            for name, (mysql_type, sqlite_type) in extras.items():
                if name in columns:
                    continue
                col_type = sqlite_type if dialect == "sqlite" else mysql_type
                conn.execute(text(f"ALTER TABLE ai_config ADD COLUMN {name} {col_type}"))
                logger.info("Added ai_config.%s", name)
    except Exception as e:
        logger.warning("Could not ensure ai_config columns: %s", e)


def _ensure_domain_dictionary_schema():
    """确保专业词典表存在，并为翻译任务补上 domain_dictionary_ids。"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        for table_name in ("domain_dictionaries", "domain_dictionary_terms"):
            if table_name not in tables and table_name in Base.metadata.tables:
                Base.metadata.tables[table_name].create(bind=engine, checkfirst=True)
                logger.info("Created %s table", table_name)
        if "literary_translations" not in tables:
            return
        columns = {column["name"] for column in inspector.get_columns("literary_translations")}
        if "domain_dictionary_ids" in columns:
            return
        if engine.dialect.name == "sqlite":
            ddl = "ALTER TABLE literary_translations ADD COLUMN domain_dictionary_ids TEXT"
        else:
            ddl = "ALTER TABLE literary_translations ADD COLUMN domain_dictionary_ids JSON NULL COMMENT '关联的专业词典ID列表'"
        with engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Added literary_translations.domain_dictionary_ids")
    except Exception as e:
        logger.warning("Could not ensure domain dictionary schema: %s", e)


def _ensure_step5_localization_schema():
    """为翻译任务与段落补上第五步本地化字段。"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        dialect = engine.dialect.name
        with engine.begin() as conn:
            if "literary_translations" in tables:
                cols = {c["name"] for c in inspector.get_columns("literary_translations")}
                if "step5_localization" not in cols:
                    if dialect == "sqlite":
                        conn.execute(text(
                            "ALTER TABLE literary_translations ADD COLUMN step5_localization TEXT"
                        ))
                    else:
                        conn.execute(text(
                            "ALTER TABLE literary_translations ADD COLUMN step5_localization TEXT NULL "
                            "COMMENT '第五步：本地化' AFTER step4_finalization"
                        ))
                    logger.info("Added literary_translations.step5_localization")
            if "literary_paragraphs" in tables:
                # refresh inspector after possible alter
                inspector = inspect(engine)
                cols = {c["name"] for c in inspector.get_columns("literary_paragraphs")}
                if "step5_localization" not in cols:
                    if dialect == "sqlite":
                        conn.execute(text(
                            "ALTER TABLE literary_paragraphs ADD COLUMN step5_localization TEXT"
                        ))
                    else:
                        conn.execute(text(
                            "ALTER TABLE literary_paragraphs ADD COLUMN step5_localization TEXT NULL "
                            "AFTER step4_finalization"
                        ))
                    logger.info("Added literary_paragraphs.step5_localization")
    except Exception as e:
        logger.warning("Could not ensure step5 localization schema: %s", e)


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
    "http://localhost:8081",   # Docker 前端端口
    "http://127.0.0.1:8081",   # Docker 前端端口
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8002",   # Docker 后端端口
    "http://127.0.0.1:8002",   # Docker 后端端口
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
app.include_router(literary_translation.router)
app.include_router(style_agents.router)
app.include_router(domain_dictionaries.router)


@app.get("/")
async def root():
    return {
        "message": "AI Translator API",
        "version": "1.0.0",
        "docs": "/docs"
    }
