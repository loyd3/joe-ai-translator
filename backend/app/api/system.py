"""
系统配置 API
"""

from fastapi import APIRouter
from app.core.ai_client import get_settings

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/config")
async def get_config():
    """获取系统配置（安全信息已脱敏）"""
    settings = get_settings()
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
    }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "ai-translator"}
