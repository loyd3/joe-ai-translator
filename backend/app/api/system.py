"""
系统配置 API（与用户绑定，需 token）
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.core.ai_client import get_settings, get_ai_client
from app.core.auth import get_current_user
from app.database import get_db
from app.models.models import AIConfig, User

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
    current_user: User = Depends(get_current_user),
):
    """获取系统配置（安全信息已脱敏，按当前用户）"""
    db_cfg = db.query(AIConfig).filter(AIConfig.user_id == current_user.id).first()
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


@router.get("/ai-config")
async def get_ai_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取大模型配置（API Key 脱敏，按当前用户）"""
    db_cfg = db.query(AIConfig).filter(AIConfig.user_id == current_user.id).first()
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
    return {
        "provider": settings.ai_provider,
        "api_key_masked": "",
        "has_api_key": bool(getattr(settings, f"{settings.ai_provider}_api_key", None)),
        "model": {
            "openai": settings.openai_model,
            "deepseek": settings.deepseek_model,
            "siliconflow": settings.siliconflow_model,
            "custom": settings.custom_model,
        }.get(settings.ai_provider, ""),
        "base_url": settings.custom_base_url or "",
        "temperature": settings.ai_temperature,
        "max_tokens": settings.ai_max_tokens,
        "source": "env",
    }


@router.put("/ai-config")
async def update_ai_config(
    request: AIConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新大模型配置（按当前用户）"""
    db_cfg = db.query(AIConfig).filter(AIConfig.user_id == current_user.id).first()
    if not db_cfg:
        db_cfg = AIConfig(user_id=current_user.id)
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
        client = get_ai_client(current_user.id)
        client.reload_from_db(current_user.id)
    except Exception:
        pass

    return {"message": "配置已保存", "provider": db_cfg.provider}


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "ai-translator"}
