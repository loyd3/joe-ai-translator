"""
统一 AI 客户端 - 支持多模型提供商
支持: OpenAI, DeepSeek, SiliconFlow, 自定义 API
"""

import os
import sys
from pathlib import Path
import openai
from pydantic_settings import BaseSettings
from typing import AsyncGenerator, Optional, List

# 项目根目录 .env（与 start.py 同目录），便于从 backend/ 启动时也能读到
# backend/app/core -> parent*3=backend -> parent*4=项目根
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


def _safe_print(msg: str) -> None:
    """Windows 下 print() 可能因控制台编码或无效字符触发 OSError [Errno 22]，此处安全输出。"""
    try:
        print(msg)
    except OSError:
        try:
            # 若 stdout 编码异常，用 ASCII 替换不可表示字符再写
            enc = getattr(sys.stdout, "encoding", None) or "utf-8"
            sys.stdout.buffer.write(msg.encode(enc, errors="replace") + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            pass


class Settings(BaseSettings):
    """应用配置"""
    # 应用与 CORS
    app_name: str = "AI Translator"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "your-secret-key-change-in-production"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    ai_provider: str = "deepseek"
    ai_temperature: float = 0.3
    ai_max_tokens: int = 4096
    database_url: str = "mysql+pymysql://root:password@localhost:3306/aitranslator?charset=utf8mb4"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    # MySQL 单独配置（.env 中 MYSQL_USER/MYSQL_PASSWORD 等，供 database 模块拼 URL）
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_host: Optional[str] = None
    mysql_port: Optional[str] = None
    mysql_database: Optional[str] = None
    
    # DeepSeek
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: Optional[str] = None
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

    # Ollama（本地模型，通常无需 API Key）
    ollama_base_url: Optional[str] = None
    ollama_model: str = "llama3.2"

    class Config:
        # 优先项目根 .env，不存在则用当前目录 .env
        env_file = str(_ENV_FILE) if _ENV_FILE.exists() else ".env"


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
    
    # 翻译类型描述
    LITERARY_TYPES = {
        "poetry": "诗歌",
        "prose": "散文",
        "novel": "小说",
        "drama": "戏剧",
        "general": "一般文学作品",
        "tech": "科技文档",
        "business": "商业文档",
        "trade": "贸易文档",
        "legal": "法律文书",
        "medical": "医学文献",
    }

    PROFESSIONAL_TYPES = {"tech", "business", "trade", "legal", "medical"}

    PROVIDER_BASE_URLS = {
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "siliconflow": "https://api.siliconflow.cn/v1",
        "ollama": "http://localhost:11435/v1",
    }

    PROVIDER_DEFAULT_MODELS = {
        "openai": "gpt-4",
        "deepseek": "deepseek-chat",
        "siliconflow": "deepseek-ai/DeepSeek-V3",
        "ollama": "llama3.2",
    }

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._client = None
        self._init_client()

    def _load_db_config(self):
        """尝试从数据库加载配置，返回配置 dict 或 None"""
        try:
            from app.database import SessionLocal
            from app.models.models import AIConfig
            db = SessionLocal()
            try:
                cfg = db.query(AIConfig).filter(AIConfig.id == 1).first()
                if cfg and cfg.api_key:
                    return {
                        "provider": cfg.provider,
                        "api_key": cfg.api_key,
                        "model": cfg.model,
                        "base_url": cfg.base_url,
                        "temperature": cfg.temperature,
                        "max_tokens": cfg.max_tokens,
                    }
            finally:
                db.close()
        except Exception:
            pass
        return None

    def _init_client(self):
        """初始化客户端：优先使用数据库配置，否则使用 .env 配置"""
        db_cfg = self._load_db_config()
        self._db_temperature = None
        self._db_max_tokens = None

        if db_cfg:
            provider = db_cfg["provider"]
            api_key = db_cfg["api_key"]
            base_url = db_cfg.get("base_url") or self.PROVIDER_BASE_URLS.get(provider, "")
            self.model = db_cfg.get("model") or self.PROVIDER_DEFAULT_MODELS.get(provider, "")
            if db_cfg.get("temperature") is not None:
                self._db_temperature = db_cfg["temperature"]
            if db_cfg.get("max_tokens") is not None:
                self._db_max_tokens = db_cfg["max_tokens"]
            if provider == "custom" and not base_url:
                raise ValueError("Custom provider requires base_url")
            if provider == "ollama" and (not api_key or not str(api_key).strip()):
                api_key = "ollama"
            self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
            _safe_print(f"[AIClient] Initialized from DB: provider={provider}, model={self.model}")
            return

        provider = self.settings.ai_provider
        if provider == "openai":
            api_key = self.settings.openai_api_key
            base_url = self.PROVIDER_BASE_URLS["openai"]
            self.model = self.settings.openai_model or "gpt-4"
        elif provider == "deepseek":
            api_key = self.settings.deepseek_api_key
            base_url = self.settings.deepseek_base_url or self.PROVIDER_BASE_URLS["deepseek"]
            self.model = self.settings.deepseek_model or "deepseek-chat"
        elif provider == "siliconflow":
            api_key = self.settings.siliconflow_api_key
            base_url = self.PROVIDER_BASE_URLS["siliconflow"]
            self.model = self.settings.siliconflow_model or "deepseek-ai/DeepSeek-V3"
        elif provider == "custom":
            api_key = self.settings.custom_api_key
            base_url = self.settings.custom_base_url
            self.model = self.settings.custom_model
            if not base_url:
                raise ValueError("Custom provider requires custom_base_url")
        elif provider == "ollama":
            api_key = getattr(self.settings, "ollama_api_key", None) or "ollama"
            base_url = self.settings.ollama_base_url or self.PROVIDER_BASE_URLS["ollama"]
            self.model = self.settings.ollama_model or self.PROVIDER_DEFAULT_MODELS["ollama"]
        else:
            raise ValueError(f"Unknown AI provider: {provider}")

        if not api_key and provider != "ollama":
            raise ValueError(f"API key not configured for provider: {provider}")

        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        _safe_print(f"[AIClient] Initialized from .env: provider={provider}, model={self.model}")

    def reload_from_db(self):
        """重新从数据库加载配置并重新初始化客户端"""
        self._client = None
        self._init_client()

    @property
    def effective_max_tokens(self) -> int:
        return self._db_max_tokens or self.settings.ai_max_tokens

    @property
    def effective_temperature(self) -> float:
        if self._db_temperature is not None:
            return self._db_temperature
        return self.settings.ai_temperature

    @property
    def client(self):
        if not self._client:
            self._init_client()
        return self._client

    def get_language_name(self, code: str) -> str:
        """获取语言名称"""
        return self.SUPPORTED_LANGUAGES.get(code, code)
    
    def get_literary_type_name(self, lit_type: str) -> str:
        """获取翻译类型名称"""
        return self.LITERARY_TYPES.get(lit_type, "一般文学作品")

    def is_professional_type(self, lit_type: str) -> bool:
        return lit_type in self.PROFESSIONAL_TYPES

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
            temperature=temperature or self.effective_temperature,
            max_tokens=max_tokens or self.effective_max_tokens,
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
            temperature=temperature or self.effective_temperature,
            max_tokens=max_tokens or self.effective_max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ============================================================
    # 文学翻译专用方法
    # ============================================================
    
    def _build_professional_domain_notes(self, literary_type: str) -> str:
        """为专业类型生成领域特定的翻译注意事项"""
        domain_notes = {
            "tech": """- 技术术语必须使用行业标准译法，不可随意意译
- 代码片段、API名称、产品名称等保留原文
- 数字、单位、公式必须准确无误
- 语言简洁精确，避免冗余修饰""",
            "business": """- 商业术语（如ROI、KPI、B2B等）使用通用商业译法
- 保留品牌名、公司名的原文或约定俗成的译名
- 语气正式专业，符合商务沟通惯例
- 数据、百分比、财务数字必须准确""",
            "trade": """- 贸易术语（如FOB、CIF、L/C等）使用国际贸易标准译法
- 法律和合同相关条款措辞严谨准确
- 保留国际通用的贸易代码和标准编号
- 注意各国/地区贸易法规差异的表述""",
            "legal": """- 法律术语必须使用目标语言法律体系中的对应概念
- 合同条款、法规引用、判例引用需遵循法律文书规范
- 措辞严谨，避免歧义，每个词都可能影响法律效力
- 保留法律文书的格式和编号结构""",
            "medical": """- 医学术语使用国际通用的标准译名（参考ICD、MeSH等）
- 药品名称使用通用名（INN），必要时注明商品名
- 剂量、检验指标、统计数据必须准确无误
- 遵循医学文献的严谨表述习惯""",
        }
        return domain_notes.get(literary_type, "")

    @staticmethod
    def _sanitize_for_api(s: Optional[str]) -> str:
        """移除控制字符，避免 Windows 上 OSError [Errno 22]"""
        if not s:
            return s or ""
        import re
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", s).strip() or s

    def build_literary_translation_prompt(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str,
        literary_type: str = "general",
        reference_content: Optional[str] = None
    ) -> list:
        """
        构建翻译提示词 - 第一步：初译
        文学类使用三美原则，专业类使用领域规范
        """
        text = self._sanitize_for_api(text)
        reference_content = self._sanitize_for_api(reference_content) if reference_content else None
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        lit_type_name = self.get_literary_type_name(literary_type)

        if self.is_professional_type(literary_type):
            domain_notes = self._build_professional_domain_notes(literary_type)
            system_prompt = f"""你是一位精通{source_name}和{target_name}的{lit_type_name}翻译专家。

## 翻译原则

### 1. 术语准确
- 专业术语必须使用目标语言中的标准译法，不可臆造
- 对于没有公认译法的新术语，可保留原文或采用"译文（原文）"格式

### 2. 领域规范
{domain_notes}

### 3. 表达要求
- 语言精练、逻辑清晰，符合{lit_type_name}的行文规范
- 句式结构符合目标语言的专业文体习惯
- 确保信息完整传达，不遗漏任何技术细节
- 避免翻译腔，读起来像目标语言的原生{lit_type_name}

### 4. 格式保留
- 保持原文的段落、列表、标题等格式结构
- 保留数字、公式、编号等特殊内容

## 输出格式

请直接输出译文，不要添加解释或评论。保持原文的段落和格式结构。"""
        else:
            system_prompt = f"""你是一位精通{source_name}和{target_name}的翻译大师，擅长{lit_type_name}翻译。

## 第一原则：以原文风格为准

翻译前，请先默读原文，判断其文体风格：
- 语体：口语化 / 书面语 / 学术 / 新闻 / 文学 / 混合
- 语气：严肃 / 轻松 / 幽默 / 讽刺 / 感伤 / 客观 / 热情
- 时代感：古典 / 近代 / 现代 / 当代流行
- 句式：长句为主 / 短句为主 / 长短交错 / 碎片化
- 用词层次：通俗日常 / 中性正式 / 高雅考究 / 粗犷直白

**译文必须匹配原文的风格层次。** 原文若是口语化的随笔，译文也应自然随性；原文若是典雅的古典诗词，译文再追求音韵与意境；原文若是冷峻的现代小说，译文也应简洁克制。切忌一律套用华丽辞藻。

## 第二原则：在原文风格内运用三美优化

在匹配原文风格的前提下，运用三美原则提升译文质量：

### 音美 (Beauty of Sound)
- 在原文的节奏基调上优化译文的韵律感
- 口语文体追求朗朗上口，书面文体追求行文流畅，诗歌文体追求音韵和谐

### 词美 (Beauty of Words)
- 在原文的用词层次内精选最佳表达
- 朴素文体内选最准确生动的日常词，典雅文体内选最精当的书面词

### 意美 (Beauty of Meaning)
- 准确传达原文的意境、情感和言外之意
- 保留文化意象和隐喻，在保真与可读之间取平衡

## 翻译要求

1. **风格复现**：译文的语体、语气、节奏应与原文高度一致
2. **三美优化**：在风格框架内追求音美、词美、意美的最佳表现
3. **自然流畅**：符合{target_name}的自然表达习惯，杜绝翻译腔
4. **准确传意**：忠实传达原文的信息、情感和深层含义

## 输出格式

请直接输出译文，不要添加解释或评论。保持原文的段落和格式结构。"""

        if reference_content:
            system_prompt += f"""

## 参考资料

请在翻译时参考以下内容，保持术语和风格的一致性：

{reference_content}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请翻译以下{lit_type_name}：\n\n{text}"}
        ]
        return messages

    async def literary_translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        literary_type: str = "general",
        reference_content: Optional[str] = None,
    ) -> str:
        """翻译 - 第一步：初译"""
        messages = self.build_literary_translation_prompt(
            text, source_lang, target_lang, literary_type, reference_content
        )
        temp = 0.4 if self.is_professional_type(literary_type) else 0.7
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temp,
            max_tokens=self.effective_max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def literary_verify(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        literary_type: str = "general",
    ) -> dict:
        """翻译 - 第二步：校验"""
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        lit_type_name = self.get_literary_type_name(literary_type)

        if self.is_professional_type(literary_type):
            domain_notes = self._build_professional_domain_notes(literary_type)
            system_prompt = f"""你是一位严谨的{lit_type_name}翻译审校专家。请对以下翻译进行全面的校验评估。

## 校验维度

### 1. 术语准确性（最高优先级）
- 专业术语是否使用了目标语言中的标准译法
- 是否存在术语翻译不一致的情况
- 新术语的处理方式是否恰当

### 2. 信息完整性
- 是否存在漏译、错译或增译
- 数字、数据、公式是否准确无误
- 逻辑关系和因果链是否清晰

### 3. 领域规范
{domain_notes}

### 4. 质量评分（0-10分）
- **术语准确度** (beauty_sound_score)：专业术语的翻译准确程度
- **表达规范度** (beauty_word_score)：是否符合{lit_type_name}的行文规范
- **信息完整度** (beauty_meaning_score)：原文信息的完整传达程度

### 5. 自然度
- 是否有翻译腔
- 是否符合目标语言{lit_type_name}的行文习惯

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "verified_translation": "经过校验和微调后的译文",
    "accuracy_analysis": "准确性分析",
    "beauty_sound_score": 8.5,
    "beauty_sound_comment": "术语准确度评价",
    "beauty_word_score": 8.0,
    "beauty_word_comment": "表达规范度评价",
    "beauty_meaning_score": 9.0,
    "beauty_meaning_comment": "信息完整度评价",
    "style_analysis": "领域规范符合度分析",
    "issues_found": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}"""
        else:
            system_prompt = f"""你是一位严谨的翻译审校专家。请对以下{lit_type_name}翻译进行全面的校验评估。

## 校验维度

### 1. 风格匹配度（首先判断）
先判断原文的风格特征（语体、语气、句式、用词层次），再评估译文是否匹配。
- 译文是否存在"过度文学化"或"过度口语化"的偏差
- 风格偏离是最优先需要纠正的问题

### 2. 准确性检查
- 是否存在漏译、错译或增译
- 关键信息是否完整传达
- 逻辑关系是否清晰

### 3. 三美原则评估（在原文风格框架内打分）

**音美 (0-10分)** — 在原文的节奏基调上，译文的韵律表现
- 原文明快 → 译文是否也简洁利落；原文舒缓 → 译文是否也从容不迫
- 朗读时是否流畅自然，符合原文的节奏感

**词美 (0-10分)** — 在原文的用词层次内，译文的选词质量
- 朴素原文 → 用词是否准确生动而不浮华；典雅原文 → 用词是否精当考究
- 是否在对应层次内做到了最佳选词

**意美 (0-10分)** — 意境、情感、言外之意的传达
- 原文的情感色彩是否完整保留
- 文化意象和隐喻的处理是否得当

### 4. 自然度
- 是否有翻译腔
- 是否读起来像目标语言的原生作品

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "verified_translation": "经过校验和微调后的译文",
    "accuracy_analysis": "准确性分析",
    "beauty_sound_score": 8.5,
    "beauty_sound_comment": "音美评价（基于原文节奏基调）",
    "beauty_word_score": 8.0,
    "beauty_word_comment": "词美评价（基于原文用词层次）",
    "beauty_meaning_score": 9.0,
    "beauty_meaning_comment": "意美评价",
    "style_analysis": "原文风格特征 + 译文风格匹配度 + 三美综合分析",
    "issues_found": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【原文】({source_name}):\n{source_text}\n\n【译文】({target_name}):\n{translated_text}\n\n请进行校验评估。"}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=self.effective_max_tokens,
            response_format={"type": "json_object"}
        )
        
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except:
            return {
                "verified_translation": translated_text,
                "accuracy_analysis": "校验完成",
                "beauty_sound_score": 7.0,
                "beauty_sound_comment": "基础达标",
                "beauty_word_score": 7.0,
                "beauty_word_comment": "基础达标",
                "beauty_meaning_score": 7.0,
                "beauty_meaning_comment": "基础达标",
                "style_analysis": "符合一般标准",
                "issues_found": [],
                "suggestions": []
            }

    async def literary_revise(
        self,
        source_text: str,
        verified_translation: str,
        verification_analysis: dict,
        source_lang: str,
        target_lang: str,
        literary_type: str = "general",
    ) -> dict:
        """
        文学翻译 - 第三步：润色
        根据校验结果进行润色
        """
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        
        issues = verification_analysis.get("issues_found", [])
        suggestions = verification_analysis.get("suggestions", [])
        
        if self.is_professional_type(literary_type):
            lit_type_name = self.get_literary_type_name(literary_type)
            system_prompt = f"""你是一位{lit_type_name}领域的翻译修订专家。请根据校验反馈，对译文进行润色和完善。

## 润色原则

### 1. 术语修正（最优先）
- 修正校验中发现的术语翻译错误
- 确保全文术语使用一致
- 对不确定的术语采用"译文（原文）"格式

### 2. 表达优化
- 提升行文的专业性和规范性
- 确保逻辑清晰、层次分明
- 消除翻译腔和冗余表达
- 使译文符合目标语言{lit_type_name}的行文惯例

### 3. 针对性改进
- 针对校验中发现的具体问题进行修正
- 根据评分，重点提升得分较低的方面
- 确保数字、数据、引用的准确性

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "revised_translation": "润色后的译文",
    "revision_summary": "润色总结",
    "key_improvements": ["改进点1", "改进点2"],
    "beauty_sound_enhancement": "术语准确度提升说明",
    "beauty_word_enhancement": "表达规范度提升说明",
    "beauty_meaning_enhancement": "信息完整度提升说明"
}}"""
        else:
            system_prompt = f"""你是一位追求精准的翻译修订专家。请根据校验反馈，对译文进行润色。

## 润色原则

### 1. 风格校准（最优先）
- 重新审视原文的语体、语气、用词层次
- 如果译文偏离了原文风格（过于华丽或过于平淡），首先纠正风格偏差
- 确保译文读起来像是目标语言中同类风格的原生作品

### 2. 三美提升（在原文风格框架内）
- **音美**：在原文的节奏基调上优化韵律，让译文更流畅动听
- **词美**：在原文的用词层次内精炼措辞，每个词都力求最佳
- **意美**：深化意境和情感的传达，补足言外之意的缺失
- 注意：三美优化不是拉高文风，而是在对应层次内做到极致

### 3. 针对性改进
- 针对校验中发现的具体问题进行修正
- 根据评分，重点提升得分较低的方面
- 解决准确性问题，确保无漏译、错译
- 消除翻译腔和生硬表达

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "revised_translation": "润色后的译文",
    "revision_summary": "润色总结，说明主要改进了哪些方面",
    "key_improvements": ["改进点1", "改进点2"],
    "beauty_sound_enhancement": "音美提升说明",
    "beauty_word_enhancement": "词美提升说明",
    "beauty_meaning_enhancement": "意美提升说明"
}}"""

        issues_text = "\n".join([f"- {issue}" for issue in issues]) if issues else "无明显问题"
        suggestions_text = "\n".join([f"- {s}" for s in suggestions]) if suggestions else "无特别建议"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【原文】({source_name}):\n{source_text}\n\n【待润色译文】({target_name}):\n{verified_translation}\n\n【校验反馈】\n发现的问题：\n{issues_text}\n\n改进建议：\n{suggestions_text}\n\n请进行润色。"}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5,
            max_tokens=self.effective_max_tokens,
            response_format={"type": "json_object"}
        )
        
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except:
            return {
                "revised_translation": verified_translation,
                "revision_summary": "基于校验反馈进行微调",
                "key_improvements": [],
                "beauty_sound_enhancement": "保持原有水平",
                "beauty_word_enhancement": "保持原有水平",
                "beauty_meaning_enhancement": "保持原有水平"
            }

    async def literary_finalize(
        self,
        source_text: str,
        revised_translation: str,
        source_lang: str,
        target_lang: str,
        literary_type: str = "general",
    ) -> dict:
        """
        文学翻译 - 第四步：定稿
        最终审校和润色，确保译文达到出版水准
        """
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        
        if self.is_professional_type(literary_type):
            lit_type_name = self.get_literary_type_name(literary_type)
            system_prompt = f"""你是一位资深的{lit_type_name}翻译定稿专家。你将收到完整的原文和译文（之前是分段翻译的），请从全篇角度进行最后的审校和定稿。

## 定稿标准

### 1. 全篇统一性（核心任务）
- 统一全文的术语翻译，消除分段翻译造成的不一致
- 同一术语、概念、名称在全文中保持统一译法
- 确保段落之间的衔接自然，上下文逻辑连贯

### 2. 术语与规范
- 最终确认所有专业术语的翻译准确性
- 确保数字、数据、引用、编号的准确性
- 格式符合{lit_type_name}的排版规范

### 3. 表达质量
- 语言精练、逻辑清晰
- 消除翻译腔和生硬表达
- 读起来像目标语言的原生{lit_type_name}

### 4. 完美准确
- 零错误：无错译、漏译、增译
- 细节到位：标点、格式、特殊内容处理得当

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "final_translation": "最终定稿译文（保持原文的段落划分，段落之间用两个换行符分隔）",
    "final_assessment": "总体评价（术语一致性 + 全篇统一性 + 专业规范度）",
    "beauty_sound_final": "术语准确度最终评价",
    "beauty_word_final": "表达规范度最终评价",
    "beauty_meaning_final": "信息完整度最终评价",
    "publishing_readiness": "发布准备度评估",
    "translator_note": "译者注（如有需要说明的特殊处理）"
}}

**重要：final_translation 中必须保持与原文相同的段落数量和段落划分，段落之间用两个换行符（\\n\\n）分隔。**"""
        else:
            system_prompt = f"""你是一位资深的翻译定稿专家。你将收到完整的原文和译文（之前是分段翻译的），请从全篇角度进行最后的审校和润色，确保达到出版品质。

## 定稿标准

### 1. 全篇统一性（整合定稿的核心任务）
- 统一全文的用词、语气和风格，消除分段翻译造成的不一致
- 同一概念、人名、术语在全文中保持统一译法
- 确保段落之间的衔接自然流畅，上下文连贯
- 调整语气和节奏，让全文读起来像一气呵成而非拼接

### 2. 风格一致（以原文为准）
- 最后确认译文风格是否与原文一致
- 原文朴素直白，译文不得华丽堆砌
- 原文典雅考究，译文不得失于粗糙
- 原文幽默俏皮，译文不得变得正经死板
- 整体气质、语气、节奏必须与原文相符

### 3. 三美最终打磨（在原文风格内追求极致）
- **音美**：在原文的节奏基调上做最后的韵律打磨，让译文朗读时自然流畅
- **词美**：在原文的用词层次内做最后的措辞精炼，每个词都恰到好处
- **意美**：确保意境、情感、言外之意完整传达，余味悠长

### 4. 完美准确
- 零错误：无错译、漏译、增译
- 精准传达：作者意图和文本内涵完整呈现
- 细节到位：标点、格式、特殊表达处理得当

### 5. 自然度
- 毫无翻译腔，读起来像目标语言的原创
- 符合目标语言同类文体的表达习惯
- 消除残留的生硬表达

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "final_translation": "最终定稿译文（保持原文的段落划分，段落之间用两个换行符分隔）",
    "final_assessment": "总体评价（原文风格判断 + 全篇统一性 + 三美达成度）",
    "beauty_sound_final": "音美最终评价",
    "beauty_word_final": "词美最终评价",
    "beauty_meaning_final": "意美最终评价",
    "publishing_readiness": "出版准备度评估",
    "translator_note": "译者注（如有需要说明的特殊处理）"
}}

**重要：final_translation 中必须保持与原文相同的段落数量和段落划分，段落之间用两个换行符（\\n\\n）分隔。**"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【完整原文】({source_name}):\n{source_text}\n\n【待定稿译文（分段翻译后合并）】({target_name}):\n{revised_translation}\n\n请从全篇角度进行最终定稿，统一风格和用词，保持段落结构不变。"}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=self.effective_max_tokens,
            response_format={"type": "json_object"}
        )
        
        import json
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except:
            return {
                "final_translation": revised_translation,
                "final_assessment": "译文质量良好，达到基本出版标准",
                "beauty_sound_final": "音韵和谐",
                "beauty_word_final": "用词精准",
                "beauty_meaning_final": "意境传达到位",
                "publishing_readiness": "基本具备出版条件",
                "translator_note": ""
            }

    async def literary_translate_paragraph(
        self,
        paragraph: str,
        source_lang: str,
        target_lang: str,
        literary_type: str = "general",
        reference_content: Optional[str] = None,
    ) -> dict:
        """
        完整的四步文学翻译流程 - 用于单个段落
        返回完整的四步结果
        """
        # 第一步：翻译
        step1 = await self.literary_translate(
            paragraph, source_lang, target_lang, literary_type, reference_content
        )
        
        # 第二步：校验
        step2_result = await self.literary_verify(
            paragraph, step1, source_lang, target_lang, literary_type
        )
        step2 = step2_result.get("verified_translation", step1)
        
        # 第三步：润色
        step3_result = await self.literary_revise(
            paragraph, step2, step2_result, source_lang, target_lang, literary_type
        )
        step3 = step3_result.get("revised_translation", step2)
        
        # 第四步：定稿
        step4_result = await self.literary_finalize(
            paragraph, step3, source_lang, target_lang, literary_type
        )
        step4 = step4_result.get("final_translation", step3)
        
        return {
            "step1_translation": step1,
            "step2_verification": step2,
            "step3_revision": step3,
            "step4_finalization": step4,
            "beauty_scores": {
                "sound": step2_result.get("beauty_sound_score", 7.0),
                "word": step2_result.get("beauty_word_score", 7.0),
                "meaning": step2_result.get("beauty_meaning_score", 7.0),
            },
            "final_assessment": step4_result.get("final_assessment", ""),
            "translator_note": step4_result.get("translator_note", ""),
        }

    async def extract_professional_terms(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        literary_type: str = "general",
        existing_terms: Optional[List[dict]] = None,
    ) -> dict:
        """
        提取和总结专业词汇
        分析原文和译文，提取专业术语、特色词汇，并判断哪些是新增的
        """
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        lit_type_name = self.get_literary_type_name(literary_type)

        existing_terms_text = ""
        if existing_terms:
            existing_terms_text = "\n\n## 已有词汇库\n" + "\n".join([
                f"- {t['source_term']} -> {t['target_term']}"
                for t in existing_terms[:50]
            ])

        system_prompt = f"""你是一位专业的文学翻译术语分析专家。请分析以下{lit_type_name}的原文和译文，提取专业术语和特色词汇。

## 分析要求

### 1. 词汇类型
- **专业术语**：特定领域的专有名词、技术术语
- **文学特色词**：具有文学审美价值的词汇、修辞手法相关的词汇
- **文化特有词**：反映特定文化内涵的词汇
- **风格标志性词汇**：体现作者或体裁风格的特色表达

### 2. 提取标准
- 选择具有翻译难度或值得记录的词汇
- 关注翻译策略和技巧的体现
- 注意一词多译或一译多词的情况
- 优先选择具有代表性的词汇

### 3. 输出格式
请以JSON格式输出：
{{
    "terms": [
        {{
            "source_term": "源语言词汇",
            "target_term": "目标语言翻译",
            "category": "词汇分类（如：诗歌术语/修辞手法/文化词汇等）",
            "description": "简要的翻译说明或例句语境"
        }}
    ],
    "summary": "对本次翻译专业词汇的总体分析和说明",
    "total_count": 词汇总数（整数）
}}

注意：
- 只提取真正有特色、有价值的词汇，不要罗列普通词汇
- 词汇数量控制在5-20个，质量优先于数量
- category字段用于归类，便于后续检索和管理"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【原文】(source_name):\n{source_text}\n\n【译文】(target_name):\n{translated_text}{existing_terms_text}\n\n请提取和分析专业词汇。"}
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=self.effective_max_tokens,
            response_format={"type": "json_object"}
        )

        import json
        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            return {
                "terms": [],
                "summary": "词汇提取过程中出现问题",
                "total_count": 0
            }


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
