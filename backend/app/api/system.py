"""
系统配置 API（可选登录：匿名使用 user_id=NULL 的全局配置）
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.core.ai_client import get_settings, get_ai_client
from app.core.auth import get_optional_user
from app.database import get_db
from app.models.models import AIConfig, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"])


PROVIDER_DEFAULTS = {
    "openai": {"model": "gpt-4", "base_url": "https://api.openai.com/v1"},
    "deepseek": {"model": "deepseek-chat", "base_url": "https://api.deepseek.com/v1"},
    "siliconflow": {"model": "deepseek-ai/DeepSeek-V3", "base_url": "https://api.siliconflow.cn/v1"},
    "custom": {"model": "", "base_url": ""},
}


@router.get("/config")
async def get_config(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取系统配置（安全信息已脱敏；匿名使用全局 user_id=NULL 配置）"""
    uid = current_user.id if current_user else None
    try:
        db_cfg = db.query(AIConfig).filter(AIConfig.user_id == uid).first()
    except OperationalError as e:
        logger.exception("ai_config table query failed: %s", e)
        err_msg = str(getattr(e, "orig", e))
        if "user_id" in err_msg and "ai_config" in err_msg:
            detail = "ai_config 表缺少 user_id 列。请执行: mysql -u root -p aitranslator < backend/migrations/add_user_id_to_ai_config.sql"
        else:
            detail = "配置表暂不可用。请重启后端以自动建表，或执行: mysql -u root -p aitranslator < backend/migrations/create_ai_config.sql"
        raise HTTPException(status_code=503, detail=detail)
    settings = get_settings()
    if db_cfg and db_cfg.api_key:
        provider = db_cfg.provider
        model = db_cfg.model or PROVIDER_DEFAULTS.get(provider, {}).get("model", "")
        return {
            "ai_provider": provider,
            "ai_model": model,
            "ai_temperature": db_cfg.temperature if db_cfg.temperature is not None else settings.ai_temperature,
            "ai_max_tokens": db_cfg.max_tokens or settings.ai_max_tokens,
            "source": "database",
        }
    return {
        "ai_provider": settings.ai_provider,
        "ai_model": {
            "openai": settings.openai_model,
            "deepseek": settings.deepseek_model,
            "siliconflow": settings.siliconflow_model,
            "custom": settings.custom_model,
        }.get(settings.ai_provider, "unknown"),
        "ai_temperature": settings.ai_temperature,
        "ai_max_tokens": settings.ai_max_tokens,
        "source": "env",
    }


class AIConfigUpdate(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


def _env_model_value(settings) -> str:
    """从 settings 取当前 provider 对应的 model 字符串，避免 KeyError 或类型异常"""
    provider = getattr(settings, "ai_provider", "deepseek") or "deepseek"
    model_map = {
        "openai": getattr(settings, "openai_model", "gpt-4"),
        "deepseek": getattr(settings, "deepseek_model", "deepseek-chat"),
        "siliconflow": getattr(settings, "siliconflow_model", "deepseek-ai/DeepSeek-V3"),
        "custom": getattr(settings, "custom_model", ""),
    }
    return model_map.get(provider, "") if isinstance(model_map.get(provider), str) else str(model_map.get(provider, ""))


@router.get("/ai-config")
async def get_ai_config(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取大模型配置（API Key 脱敏；匿名使用全局配置）"""
    uid = current_user.id if current_user else None
    try:
        db_cfg = db.query(AIConfig).filter(AIConfig.user_id == uid).first()
    except OperationalError as e:
        logger.exception("ai_config table query failed: %s", e)
        err_msg = str(getattr(e, "orig", e))
        if "user_id" in err_msg and "ai_config" in err_msg:
            detail = "ai_config 表缺少 user_id 列。请执行: mysql -u root -p aitranslator < backend/migrations/add_user_id_to_ai_config.sql"
        else:
            detail = "配置表暂不可用。请重启后端以自动建表，或执行: mysql -u root -p aitranslator < backend/migrations/create_ai_config.sql"
        raise HTTPException(status_code=503, detail=detail)
    settings = get_settings()
    if db_cfg:
        masked_key = ""
        if db_cfg.api_key:
            k = db_cfg.api_key
            masked_key = k[:6] + "****" + k[-4:] if len(k) > 10 else "****"
        return {
            "provider": db_cfg.provider,
            "api_key_masked": masked_key,
            "has_api_key": bool(db_cfg.api_key),
            "model": db_cfg.model or "",
            "base_url": db_cfg.base_url or "",
            "temperature": db_cfg.temperature if db_cfg.temperature is not None else settings.ai_temperature,
            "max_tokens": db_cfg.max_tokens or settings.ai_max_tokens,
            "source": "database",
        }
    provider = getattr(settings, "ai_provider", "deepseek") or "deepseek"
    api_key_attr = f"{provider}_api_key" if provider in ("openai", "deepseek", "siliconflow", "custom") else "deepseek_api_key"
    has_key = bool(getattr(settings, api_key_attr, None))
    return {
        "provider": provider,
        "api_key_masked": "",
        "has_api_key": has_key,
        "model": _env_model_value(settings),
        "base_url": getattr(settings, "custom_base_url", "") or "",
        "temperature": getattr(settings, "ai_temperature", 0.3),
        "max_tokens": getattr(settings, "ai_max_tokens", 4096),
        "source": "env",
    }


@router.put("/ai-config")
async def update_ai_config(
    request: AIConfigUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """更新大模型配置（匿名写入 user_id=NULL 的全局配置）"""
    uid = current_user.id if current_user else None
    db_cfg = db.query(AIConfig).filter(AIConfig.user_id == uid).first()
    if not db_cfg:
        db_cfg = AIConfig(user_id=uid)
        db.add(db_cfg)

    db_cfg.provider = request.provider
    if request.api_key is not None:
        db_cfg.api_key = request.api_key
    if request.model is not None:
        db_cfg.model = request.model
    if request.base_url is not None:
        db_cfg.base_url = request.base_url
    if request.temperature is not None:
        db_cfg.temperature = request.temperature
    if request.max_tokens is not None:
        db_cfg.max_tokens = request.max_tokens

    db.commit()
    db.refresh(db_cfg)

    try:
        client = get_ai_client(uid)
        client.reload_from_db(uid)
    except Exception:
        pass

    return {"message": "配置已保存", "provider": db_cfg.provider}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "ai-translator"}
