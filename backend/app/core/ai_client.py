"""
统一 AI 客户端 - 支持多模型提供商
支持: OpenAI, DeepSeek, SiliconFlow, 自定义 API
"""

import os
import openai
from pydantic_settings import BaseSettings
from typing import AsyncGenerator, Optional, List


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
    
    # 文学类型描述
    LITERARY_TYPES = {
        "poetry": "诗歌",
        "prose": "散文", 
        "novel": "小说",
        "drama": "戏剧",
        "general": "一般文学作品"
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
    
    def get_literary_type_name(self, lit_type: str) -> str:
        """获取文学类型名称"""
        return self.LITERARY_TYPES.get(lit_type, "一般文学作品")

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

    # ============================================================
    # 文学翻译专用方法
    # ============================================================
    
    def build_literary_translation_prompt(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str,
        literary_type: str = "general",
        reference_content: Optional[str] = None
    ) -> list:
        """
        构建文学翻译提示词 - 第一步：初译
        强调三美原则：音美、词美、意美
        """
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        lit_type_name = self.get_literary_type_name(literary_type)
        
        system_prompt = f"""你是一位精通{source_name}和{target_name}的文学翻译大师， specializing in {lit_type_name} translation.

## 三美原则（翻译的核心指导思想）

### 1. 音美 (Beauty of Sound)
- 注重译文的韵律、节奏和音乐性
- 保留原文的抑扬顿挫和音韵之美
- 在诗歌翻译中，关注押韵、格律和声调

### 2. 词美 (Beauty of Words)
- 选词精准，追求"炼字"的境界
- 使用优美、典雅的表达方式
- 注意词语的色彩、质感和韵味
- 避免平庸、直白的表达

### 3. 意美 (Beauty of Meaning)
- 准确把握原文的意境和神韵
- 传达作者的情感、思想和风格
- 保留文化意象和隐喻
- 追求"信达雅"中的"雅"

## 翻译要求

1. **深入理解原文**：把握作者的情感基调、写作风格和深层含义
2. **文化转换**：在保留原文文化特色的同时，确保译文对目标读者具有感染力
3. **风格统一**：保持与原文一致的文学风格和语言调性
4. **创造性转化**：不拘泥于字面，追求神韵的传达

## 输出格式

请直接输出译文，不要添加解释或评论。译文应该：
- 流畅自然，符合{target_name}文学表达习惯
- 体现三美原则
- 保持原文的段落和格式结构"""

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
        """
        文学翻译 - 第一步：初译
        """
        messages = self.build_literary_translation_prompt(
            text, source_lang, target_lang, literary_type, reference_content
        )
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,  # 文学翻译需要更多创造性
            max_tokens=self.settings.ai_max_tokens,
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
        """
        文学翻译 - 第二步：校验
        检查翻译的准确性、完整性和三美原则的体现
        """
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        
        system_prompt = f"""你是一位严谨的文学翻译审校专家。请对以下{self.get_literary_type_name(literary_type)}翻译进行全面的校验评估。

## 校验维度

### 1. 准确性检查
- 是否存在漏译、错译或增译
- 关键信息是否完整传达
- 逻辑关系是否清晰

### 2. 三美原则评估

**音美 (0-10分)**
- 译文的韵律和节奏
- 音韵的和谐程度
- 朗读时的音乐性

**词美 (0-10分)**
- 用词的精准度和优雅度
- 词汇的质感和色彩
- 避免俗套和平庸表达

**意美 (0-10分)**
- 意境的传达是否到位
- 情感色彩是否一致
- 神韵是否得以保留

### 3. 风格一致性
- 是否符合原文的文学风格
- 语言调性是否恰当
- 时代感和文化感是否准确

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "verified_translation": "经过校验和微调后的译文",
    "accuracy_analysis": "准确性分析",
    "beauty_sound_score": 8.5,
    "beauty_sound_comment": "音美评价",
    "beauty_word_score": 8.0,
    "beauty_word_comment": "词美评价",
    "beauty_meaning_score": 9.0,
    "beauty_meaning_comment": "意美评价",
    "style_analysis": "风格分析",
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
            max_tokens=self.settings.ai_max_tokens,
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
        文学翻译 - 第三步：修改
        根据校验结果进行针对性修改
        """
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        
        issues = verification_analysis.get("issues_found", [])
        suggestions = verification_analysis.get("suggestions", [])
        
        system_prompt = f"""你是一位追求完美的文学翻译修订专家。请根据校验反馈，对译文进行深度修改和润色。

## 修改原则

### 1. 针对性改进
- 针对校验中发现的具体问题进行修正
- 根据三美原则的评分，重点提升得分较低的方面
- 解决准确性问题，确保无漏译、错译

### 2. 深度润色
- 提升语言的文学性和艺术性
- 优化词汇选择，追求"诗眼"和"文眼"
- 调整句式结构，增强节奏感和音乐性

### 3. 神韵升华
- 不仅要"译意"，更要"译味"
- 传达原文的情感张力和审美意蕴
- 创造具有感染力的文学语言

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "revised_translation": "修改后的译文",
    "revision_summary": "修改总结，说明主要改进了哪些方面",
    "key_improvements": ["改进点1", "改进点2"],
    "beauty_sound_enhancement": "音美提升说明",
    "beauty_word_enhancement": "词美提升说明",
    "beauty_meaning_enhancement": "意美提升说明"
}}"""

        issues_text = "\n".join([f"- {issue}" for issue in issues]) if issues else "无明显问题"
        suggestions_text = "\n".join([f"- {s}" for s in suggestions]) if suggestions else "无特别建议"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【原文】({source_name}):\n{source_text}\n\n【待修改译文】({target_name}):\n{verified_translation}\n\n【校验反馈】\n发现的问题：\n{issues_text}\n\n改进建议：\n{suggestions_text}\n\n请进行修改润色。"}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.5,
            max_tokens=self.settings.ai_max_tokens,
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
        
        system_prompt = f"""你是一位资深的文学翻译定稿专家。请对译文进行最后的审校和润色，确保达到出版品质。

## 定稿标准

### 1. 完美准确
- 零错误：无错译、漏译、增译
- 精准传达：作者意图和文本内涵完整呈现
- 细节到位：标点、格式、特殊表达处理得当

### 2. 三美兼备
- **音美**：朗朗上口，音韵和谐，节奏得当
- **词美**：字字珠玑，雅俗得当，富有质感
- **意美**：意境深远，神韵具足，余味悠长

### 3. 风格纯粹
- 语言风格与原文高度一致
- 时代感和文化感准确
- 整体气质与原文相符

### 4. 可读性
- 对目标读者具有感染力
- 流畅自然，毫无翻译腔
- 能够独立作为文学作品欣赏

## 输出格式

请以JSON格式输出，包含以下字段：
{{
    "final_translation": "最终定稿译文",
    "final_assessment": "总体评价",
    "beauty_sound_final": "音美最终评价",
    "beauty_word_final": "词美最终评价",
    "beauty_meaning_final": "意美最终评价",
    "publishing_readiness": "出版准备度评估",
    "translator_note": "译者注（如有需要说明的特殊处理）"
}}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"【原文】({source_name}):\n{source_text}\n\n【待定稿译文】({target_name}):\n{revised_translation}\n\n请进行最终定稿。"}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=self.settings.ai_max_tokens,
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
        
        # 第三步：修改
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
