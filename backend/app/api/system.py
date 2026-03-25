"""
系统配置 API（可选登录：匿名使用 user_id=NULL 的全局配置）
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError

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
    "ollama": {"model": "qwen2.5:7b", "base_url": "http://127.0.0.1:11434/v1"},
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
            "ollama": settings.ollama_model,
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


def _normalize_provider(provider: str) -> str:
    p = (provider or "").strip().lower()
    if p not in PROVIDER_DEFAULTS:
        raise HTTPException(status_code=400, detail=f"不支持的 provider: {provider}")
    return p


def _env_model_value(settings) -> str:
    """从 settings 取当前 provider 对应的 model 字符串，避免 KeyError 或类型异常"""
    provider = getattr(settings, "ai_provider", "deepseek") or "deepseek"
    model_map = {
        "openai": getattr(settings, "openai_model", "gpt-4"),
        "deepseek": getattr(settings, "deepseek_model", "deepseek-chat"),
        "siliconflow": getattr(settings, "siliconflow_model", "deepseek-ai/DeepSeek-V3"),
        "ollama": getattr(settings, "ollama_model", "qwen2.5:7b"),
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
    if provider == "ollama":
        api_key_attr = "ollama_api_key"
    has_key = bool(getattr(settings, api_key_attr, None))
    return {
        "provider": provider,
        "api_key_masked": "",
        "has_api_key": has_key,
        "model": _env_model_value(settings),
        "base_url": (getattr(settings, "ollama_base_url", "") if provider == "ollama" else getattr(settings, "custom_base_url", "")) or "",
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
    provider = _normalize_provider(request.provider)
    try:
        db_cfg = db.query(AIConfig).filter(AIConfig.user_id == uid).first()
        if not db_cfg:
            db_cfg = AIConfig(user_id=uid)
            db.add(db_cfg)

        db_cfg.provider = provider
        if request.api_key is not None:
            db_cfg.api_key = request.api_key
        if request.model is not None:
            db_cfg.model = request.model
        elif not db_cfg.model:
            db_cfg.model = PROVIDER_DEFAULTS.get(provider, {}).get("model", "")
        if request.base_url is not None:
            db_cfg.base_url = request.base_url
        elif provider == "ollama" and not db_cfg.base_url:
            db_cfg.base_url = PROVIDER_DEFAULTS["ollama"]["base_url"]
        if request.temperature is not None:
            db_cfg.temperature = request.temperature
        if request.max_tokens is not None:
            db_cfg.max_tokens = request.max_tokens

        # Ollama 不要求真实 API key，确保客户端初始化不失败
        if provider == "ollama" and not db_cfg.api_key:
            db_cfg.api_key = "ollama"

        db.commit()
        db.refresh(db_cfg)
    except OperationalError as e:
        db.rollback()
        logger.exception("update ai_config failed: %s", e)
        err_msg = str(getattr(e, "orig", e))
        if "Field 'id' doesn't have a default value" in err_msg and "ai_config" in err_msg:
            raise HTTPException(
                status_code=503,
                detail="保存失败：ai_config.id 不是自增列。请执行: mysql -u root -p aitranslator < backend/migrations/007_fix_ai_config_id_autoincrement.sql",
            )
        raise HTTPException(status_code=503, detail="保存失败：数据库表结构未就绪，请执行 ai_config 迁移")
    except IntegrityError as e:
        db.rollback()
        logger.exception("update ai_config integrity failed: %s", e)
        raise HTTPException(status_code=400, detail="保存失败：配置冲突，请稍后重试")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("update ai_config unknown failed: %s", e)
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

    try:
        client = get_ai_client(uid)
        client.reload_from_db(uid)
    except Exception as e:
        logger.warning("reload ai client failed after save: %s", e)

    return {"message": "配置已保存", "provider": db_cfg.provider}


@router.get("/active-model")
async def get_active_model(current_user: Optional[User] = Depends(get_optional_user)):
    """返回当前实际生效的模型配置（用于前端展示当前正在用哪个模型）"""
    uid = current_user.id if current_user else None
    try:
        client = get_ai_client(uid)
        provider = getattr(getattr(client, "settings", None), "ai_provider", None)
        if hasattr(client, "_load_db_config"):
            cfg = client._load_db_config()  # noqa: SLF001
            if cfg and cfg.get("provider"):
                provider = cfg.get("provider")
                base_url = cfg.get("base_url") or PROVIDER_DEFAULTS.get(provider, {}).get("base_url", "")
                return {
                    "provider": provider,
                    "model": getattr(client, "model", ""),
                    "base_url": base_url,
                    "source": "database",
                }
        settings = getattr(client, "settings", None)
        provider = provider or getattr(settings, "ai_provider", "deepseek")
        base_url = {
            "deepseek": getattr(settings, "deepseek_base_url", "") or PROVIDER_DEFAULTS["deepseek"]["base_url"],
            "openai": PROVIDER_DEFAULTS["openai"]["base_url"],
            "siliconflow": PROVIDER_DEFAULTS["siliconflow"]["base_url"],
            "ollama": getattr(settings, "ollama_base_url", "") or PROVIDER_DEFAULTS["ollama"]["base_url"],
            "custom": getattr(settings, "custom_base_url", "") or "",
        }.get(provider, "")
        return {
            "provider": provider,
            "model": getattr(client, "model", ""),
            "base_url": base_url,
            "source": "env",
        }
    except Exception as e:
        logger.exception("get active model failed: %s", e)
        raise HTTPException(status_code=500, detail=f"获取当前模型失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "ai-translator"}
