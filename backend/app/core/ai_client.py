"""
统一 AI 客户端 - 支持多模型提供商
支持: OpenAI, DeepSeek, SiliconFlow, 自定义 API
"""

import os
import openai
from pydantic_settings import BaseSettings
from typing import AsyncGenerator, Optional


class Settings(BaseSettings):
    """应用配置"""
    ai_provider: str = "deepseek"
    ai_temperature: float = 0.3
    ai_max_tokens: int = 4096
    database_url: str = "mysql+pymysql://root:password@localhost:3306/aitranslator?charset=utf8mb4"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    
    # DeepSeek
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    
    # SiliconFlow
    siliconflow_api_key: Optional[str] = None
    siliconflow_model: str = "deepseek-ai/DeepSeek-V3"
    
    # Custom
    custom_api_key: Optional[str] = None
    custom_base_url: Optional[str] = None
    custom_model: Optional[str] = None
    
    class Config:
        env_file = ".env"


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


class AIClient:
    """统一的 AI 客户端，支持多个模型提供商"""
    
    # 支持的语言列表
    SUPPORTED_LANGUAGES = {
        "auto": "自动检测",
        "zh": "中文",
        "zh-TW": "繁体中文",
        "en": "英语",
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "it": "意大利语",
        "pt": "葡萄牙语",
        "ru": "俄语",
        "ar": "阿拉伯语",
        "hi": "印地语",
        "th": "泰语",
        "vi": "越南语",
        "id": "印尼语",
        "ms": "马来语",
        "tr": "土耳其语",
        "pl": "波兰语",
        "nl": "荷兰语",
        "sv": "瑞典语",
        "cs": "捷克语",
        "el": "希腊语",
        "he": "希伯来语",
        "ro": "罗马尼亚语",
        "hu": "匈牙利语",
        "da": "丹麦语",
        "fi": "芬兰语",
        "no": "挪威语",
        "uk": "乌克兰语",
    }

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._client = None
        self._init_client()

    def _init_client(self):
        """根据配置的 provider 初始化对应的客户端"""
        provider = self.settings.ai_provider

        if provider == "openai":
            api_key = self.settings.openai_api_key
            base_url = "https://api.openai.com/v1"
            self.model = self.settings.openai_model or "gpt-4"
        elif provider == "deepseek":
            api_key = self.settings.deepseek_api_key
            base_url = "https://api.deepseek.com/v1"
            self.model = self.settings.deepseek_model or "deepseek-chat"
        elif provider == "siliconflow":
            api_key = self.settings.siliconflow_api_key
            base_url = "https://api.siliconflow.cn/v1"
            self.model = self.settings.siliconflow_model or "deepseek-ai/DeepSeek-V3"
        elif provider == "custom":
            api_key = self.settings.custom_api_key
            base_url = self.settings.custom_base_url
            self.model = self.settings.custom_model
            if not base_url:
                raise ValueError("Custom provider requires custom_base_url")
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

        if not api_key:
            raise ValueError(f"API key not configured for provider: {provider}")

        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        print(f"[AIClient] Initialized with provider: {provider}, model: {self.model}")

    @property
    def client(self):
        if not self._client:
            self._init_client()
        return self._client

    def get_language_name(self, code: str) -> str:
        """获取语言名称"""
        return self.SUPPORTED_LANGUAGES.get(code, code)

    def build_translation_prompt(self, text: str, source_lang: str, target_lang: str, context: Optional[str] = None) -> list:
        """构建翻译提示词"""
        source_name = self.get_language_name(source_lang) if source_lang != "auto" else "检测到的语言"
        target_name = self.get_language_name(target_lang)
        
        system_prompt = f"""You are a professional translator. Translate the following text from {source_name} to {target_name}.

Requirements:
1. Maintain the original meaning accurately
2. Preserve formatting (markdown, line breaks, etc.)
3. Use natural and fluent expressions in the target language
4. Keep technical terms accurate
5. Do not add explanations unless specifically requested

Output only the translated text, no additional comments."""

        if context:
            system_prompt += f"\n\nContext: {context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        return messages

    async def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """翻译文本（非流式）"""
        messages = self.build_translation_prompt(text, source_lang, target_lang, context)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.settings.ai_temperature,
            max_tokens=max_tokens or self.settings.ai_max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def translate_stream(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en",
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """翻译文本（流式）"""
        messages = self.build_translation_prompt(text, source_lang, target_lang, context)
        
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.settings.ai_temperature,
            max_tokens=max_tokens or self.settings.ai_max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# 全局客户端实例（延迟初始化）
_ai_client_instance: Optional[AIClient] = None


def get_ai_client() -> AIClient:
    """获取 AI 客户端实例（延迟初始化）"""
    global _ai_client_instance
    if _ai_client_instance is None:
        _ai_client_instance = AIClient()
    return _ai_client_instance


# 向后兼容 - 使用属性访问器实现真正的延迟加载
class _LazyAIClient:
    """延迟加载的 AI 客户端代理"""

    _client: Optional[AIClient] = None

    def _get_client(self):
        if self._client is None:
            self._client = get_ai_client()
        return self._client

    def __getattr__(self, name):
        return getattr(self._get_client(), name)

    async def translate(self, *args, **kwargs):
        return await self._get_client().translate(*args, **kwargs)

    async def translate_stream(self, *args, **kwargs):
        async for chunk in self._get_client().translate_stream(*args, **kwargs):
            yield chunk


ai_client = _LazyAIClient()
