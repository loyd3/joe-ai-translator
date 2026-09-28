"""
系统配置 API
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
import openai

from app.core.ai_client import get_settings, get_ai_client
from app.database import get_db
from app.models.models import AIConfig

router = APIRouter(prefix="/api/system", tags=["system"])


PROVIDER_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "description": "性价比高，中文与长文翻译表现好",
        "base_url": "https://api.deepseek.com/v1",
        "docs_url": "https://platform.deepseek.com",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "description": "GPT 系列，通用能力强",
        "base_url": "https://api.openai.com/v1",
        "docs_url": "https://platform.openai.com",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4-turbo", "gpt-4", "o3-mini"],
        "default_model": "gpt-4o",
    },
    {
        "id": "siliconflow",
        "name": "SiliconFlow",
        "description": "硅基流动，聚合多款开源模型",
        "base_url": "https://api.siliconflow.cn/v1",
        "docs_url": "https://cloud.siliconflow.cn",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": [
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            "Qwen/Qwen2.5-72B-Instruct",
            "Qwen/Qwen2.5-32B-Instruct",
            "THUDM/glm-4-9b-chat",
        ],
        "default_model": "deepseek-ai/DeepSeek-V3",
    },
    {
        "id": "moonshot",
        "name": "Moonshot (Kimi)",
        "description": "月之暗面 Kimi，长上下文友好",
        "base_url": "https://api.moonshot.cn/v1",
        "docs_url": "https://platform.moonshot.cn",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-latest"],
        "default_model": "moonshot-v1-128k",
    },
    {
        "id": "qwen",
        "name": "通义千问",
        "description": "阿里云 DashScope 兼容模式",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "docs_url": "https://help.aliyun.com/zh/model-studio/",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
        "default_model": "qwen-plus",
    },
    {
        "id": "zhipu",
        "name": "智谱 GLM",
        "description": "智谱清言开放平台",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "docs_url": "https://open.bigmodel.cn",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": ["glm-4-flash", "glm-4-air", "glm-4-plus", "glm-4"],
        "default_model": "glm-4-flash",
    },
    {
        "id": "groq",
        "name": "Groq",
        "description": "极速推理，适合快速试译",
        "base_url": "https://api.groq.com/openai/v1",
        "docs_url": "https://console.groq.com",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "default_model": "llama-3.3-70b-versatile",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "description": "统一入口调用多家模型",
        "base_url": "https://openrouter.ai/api/v1",
        "docs_url": "https://openrouter.ai",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": [
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-001",
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct",
        ],
        "default_model": "openai/gpt-4o-mini",
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "description": "本地模型，通常无需 API Key",
        "base_url": "http://localhost:11434/v1",
        "docs_url": "https://ollama.com",
        "requires_api_key": False,
        "allow_base_url_override": True,
        "models": ["llama3.2", "qwen2.5", "qwen3.5:latest", "mistral", "gemma2"],
        "default_model": "llama3.2",
    },
    {
        "id": "custom",
        "name": "自定义",
        "description": "任意兼容 OpenAI Chat Completions 的接口",
        "base_url": "",
        "docs_url": "",
        "requires_api_key": True,
        "allow_base_url_override": True,
        "models": [],
        "default_model": "",
    },
]

PROVIDER_DEFAULTS = {
    p["id"]: {"model": p["default_model"], "base_url": p["base_url"]}
    for p in PROVIDER_CATALOG
}


def _catalog_map() -> Dict[str, Dict[str, Any]]:
    return {p["id"]: p for p in PROVIDER_CATALOG}


def _mask_key(key: Optional[str]) -> str:
    if not key:
        return ""
    k = str(key)
    return k[:6] + "****" + k[-4:] if len(k) > 10 else "****"


def _serialize_config(db_cfg: AIConfig, settings) -> Dict[str, Any]:
    return {
        "provider": db_cfg.provider,
        "api_key_masked": _mask_key(db_cfg.api_key),
        "has_api_key": bool(db_cfg.api_key),
        "model": db_cfg.model or "",
        "base_url": db_cfg.base_url or "",
        "temperature": db_cfg.temperature if db_cfg.temperature is not None else settings.ai_temperature,
        "max_tokens": db_cfg.max_tokens or settings.ai_max_tokens,
        "top_p": db_cfg.top_p if db_cfg.top_p is not None else 1.0,
        "frequency_penalty": db_cfg.frequency_penalty if db_cfg.frequency_penalty is not None else 0.0,
        "presence_penalty": db_cfg.presence_penalty if db_cfg.presence_penalty is not None else 0.0,
        "timeout_seconds": db_cfg.timeout_seconds if db_cfg.timeout_seconds is not None else 120,
        "source": "database",
        "available_providers": PROVIDER_CATALOG,
    }


@router.get("/config")
async def get_config(db: Session = Depends(get_db)):
    """获取系统配置（安全信息已脱敏）"""
    db_cfg = db.query(AIConfig).filter(AIConfig.id == 1).first()
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
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=256, le=256000)
    top_p: Optional[float] = Field(None, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(None, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(None, ge=-2, le=2)
    timeout_seconds: Optional[int] = Field(None, ge=10, le=600)


class AIConfigTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = 0.2
    timeout_seconds: Optional[int] = 30


@router.get("/ai-providers")
async def list_ai_providers():
    """可用大模型提供商与推荐模型列表。"""
    return {"providers": PROVIDER_CATALOG}


@router.get("/ai-config")
async def get_ai_config(db: Session = Depends(get_db)):
    """获取大模型配置（API Key 脱敏）"""
    db_cfg = db.query(AIConfig).filter(AIConfig.id == 1).first()
    settings = get_settings()
    if db_cfg:
        return _serialize_config(db_cfg, settings)

    catalog = _catalog_map().get(settings.ai_provider, {})
    env_model = {
        "openai": settings.openai_model,
        "deepseek": settings.deepseek_model,
        "siliconflow": settings.siliconflow_model,
        "ollama": settings.ollama_model,
        "custom": settings.custom_model,
    }.get(settings.ai_provider, catalog.get("default_model", ""))
    env_base = ""
    if settings.ai_provider == "ollama":
        env_base = settings.ollama_base_url or catalog.get("base_url", "")
    elif settings.ai_provider == "custom":
        env_base = settings.custom_base_url or ""
    else:
        env_base = catalog.get("base_url", "")

    has_key = True if settings.ai_provider == "ollama" else bool(
        getattr(settings, f"{settings.ai_provider}_api_key", None)
    )
    return {
        "provider": settings.ai_provider,
        "api_key_masked": "",
        "has_api_key": has_key,
        "model": env_model or "",
        "base_url": env_base or "",
        "temperature": settings.ai_temperature,
        "max_tokens": settings.ai_max_tokens,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "timeout_seconds": 120,
        "source": "env",
        "available_providers": PROVIDER_CATALOG,
    }


@router.put("/ai-config")
async def update_ai_config(request: AIConfigUpdate, db: Session = Depends(get_db)):
    """更新大模型配置"""
    catalog = _catalog_map()
    if request.provider not in catalog:
        raise HTTPException(status_code=400, detail=f"不支持的提供商: {request.provider}")

    meta = catalog[request.provider]
    db_cfg = db.query(AIConfig).filter(AIConfig.id == 1).first()
    if not db_cfg:
        db_cfg = AIConfig(id=1)
        db.add(db_cfg)

    provider_changed = (db_cfg.provider or "") != request.provider
    db_cfg.provider = request.provider
    if request.api_key is not None:
        db_cfg.api_key = request.api_key
    if request.provider == "ollama" and (not db_cfg.api_key or not str(db_cfg.api_key).strip()):
        db_cfg.api_key = "ollama"

    defaults = PROVIDER_DEFAULTS.get(request.provider, {})
    # 切换提供商时，未显式传入的 model/base_url 回落到该提供商默认值，避免残留旧地址
    if request.model is not None:
        db_cfg.model = request.model.strip() if request.model else None
    elif provider_changed or not (db_cfg.model or "").strip():
        db_cfg.model = defaults.get("model") or meta.get("default_model") or db_cfg.model

    if request.base_url is not None:
        db_cfg.base_url = request.base_url.strip() or None
    elif provider_changed:
        db_cfg.base_url = defaults.get("base_url") or meta.get("base_url") or None
    elif not (db_cfg.base_url or "").strip() and request.provider != "custom":
        db_cfg.base_url = defaults.get("base_url") or meta.get("base_url") or None

    if request.provider == "custom":
        if not (db_cfg.base_url or "").strip():
            raise HTTPException(status_code=400, detail="自定义提供商需要填写 API 地址")
    elif not (db_cfg.model or "").strip():
        db_cfg.model = defaults.get("model") or meta.get("default_model") or db_cfg.model

    if meta.get("requires_api_key") and not (db_cfg.api_key or "").strip():
        raise HTTPException(status_code=400, detail="请先填写 API Key")

    if request.temperature is not None:
        db_cfg.temperature = request.temperature
    if request.max_tokens is not None:
        db_cfg.max_tokens = request.max_tokens
    if request.top_p is not None:
        db_cfg.top_p = request.top_p
    if request.frequency_penalty is not None:
        db_cfg.frequency_penalty = request.frequency_penalty
    if request.presence_penalty is not None:
        db_cfg.presence_penalty = request.presence_penalty
    if request.timeout_seconds is not None:
        db_cfg.timeout_seconds = request.timeout_seconds

    db.commit()
    db.refresh(db_cfg)

    try:
        client = get_ai_client()
        client.reload_from_db()
    except Exception:
        pass

    return {
        "message": "配置已保存",
        "provider": db_cfg.provider,
        "model": db_cfg.model,
        "base_url": db_cfg.base_url or "",
    }


@router.post("/ai-config/test")
async def test_ai_config(request: AIConfigTestRequest, db: Session = Depends(get_db)):
    """用当前表单（或已保存配置）测试大模型连通性。"""
    catalog = _catalog_map()
    if request.provider not in catalog:
        raise HTTPException(status_code=400, detail=f"不支持的提供商: {request.provider}")

    meta = catalog[request.provider]
    db_cfg = db.query(AIConfig).filter(AIConfig.id == 1).first()

    api_key = (request.api_key or "").strip()
    if not api_key and db_cfg and db_cfg.provider == request.provider:
        api_key = (db_cfg.api_key or "").strip()
    if request.provider == "ollama" and not api_key:
        api_key = "ollama"
    if meta.get("requires_api_key") and not api_key:
        raise HTTPException(status_code=400, detail="请输入 API Key 后再测试")

    base_url = (request.base_url or "").strip()
    if not base_url:
        if db_cfg and db_cfg.provider == request.provider and db_cfg.base_url:
            base_url = db_cfg.base_url
        else:
            base_url = meta.get("base_url") or ""
    if request.provider == "custom" and not base_url:
        raise HTTPException(status_code=400, detail="自定义提供商需要填写 API 地址")

    model = (request.model or "").strip()
    if not model:
        if db_cfg and db_cfg.provider == request.provider and db_cfg.model:
            model = db_cfg.model
        else:
            model = meta.get("default_model") or ""
    if not model:
        raise HTTPException(status_code=400, detail="请填写模型名称")

    timeout = request.timeout_seconds or 30
    try:
        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            temperature=request.temperature if request.temperature is not None else 0.2,
            max_tokens=16,
        )
        text = (response.choices[0].message.content or "").strip()
        return {
            "success": True,
            "message": f"连接成功（{request.provider} / {model}）",
            "response": text[:200],
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)[:500] or "连接失败",
            "response": "",
        }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "ai-translator"}
