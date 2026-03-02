"""
Pydantic 数据模型
"""

from pydantic import BaseModel, Field, field_serializer
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TranslationRequest(BaseModel):
    """翻译请求"""
    text: str = Field(..., min_length=1, description="要翻译的文本")
    source_lang: str = Field(default="auto", description="源语言代码")
    target_lang: str = Field(..., description="目标语言代码")
    context: Optional[str] = Field(default=None, description="翻译上下文")
    stream: bool = Field(default=False, description="是否使用流式响应")


class TranslationResponse(BaseModel):
    """翻译响应"""
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    detected_lang: Optional[str] = None


class TranslationHistoryItem(BaseModel):
    """翻译历史记录项"""
    id: int
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    is_favorite: bool
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


class BatchTranslationRequest(BaseModel):
    """批量翻译请求"""
    items: List[str] = Field(..., min_length=1, description="要翻译的文本列表")
    source_lang: str = Field(default="auto", description="源语言代码")
    target_lang: str = Field(..., description="目标语言代码")
    context: Optional[str] = Field(default=None, description="翻译上下文")


class BatchTranslationItem(BaseModel):
    """批量翻译项目"""
    id: int
    source_text: str
    translated_text: Optional[str] = None
    status: str


class BatchTranslationResponse(BaseModel):
    """批量翻译响应"""
    id: int
    name: Optional[str] = None
    source_lang: str
    target_lang: str
    total_items: int
    completed_items: int
    status: str
    items: List[BatchTranslationItem]
    created_at: datetime
    completed_at: Optional[datetime] = None

    @field_serializer('created_at', 'completed_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


class LanguageInfo(BaseModel):
    """语言信息"""
    code: str
    name: str


# ============================================================
# 文学翻译相关 Schemas
# ============================================================

class LiteraryType(str, Enum):
    """翻译类型"""
    # 文学类
    POETRY = "poetry"       # 诗歌
    PROSE = "prose"         # 散文
    NOVEL = "novel"         # 小说
    DRAMA = "drama"         # 戏剧
    GENERAL = "general"     # 一般文学
    # 专业类
    TECH = "tech"           # 科技
    BUSINESS = "business"   # 商业
    TRADE = "trade"         # 贸易
    LEGAL = "legal"         # 法律
    MEDICAL = "medical"     # 医学


class DocType(str, Enum):
    """参考文档类型"""
    TERMINOLOGY = "terminology"     # 术语库
    STYLE_GUIDE = "style_guide"     # 风格指南
    REFERENCE = "reference"         # 参考译文
    GENERAL = "general"             # 一般文档


class TranslationStep(int, Enum):
    """翻译步骤"""
    TRANSLATE = 1       # 翻译
    VERIFY = 2          # 校验
    REVISE = 3          # 修改
    FINALIZE = 4        # 定稿


# ----- 参考文档 Schemas -----

class ReferenceDocumentCreate(BaseModel):
    """创建参考文档请求"""
    name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    doc_type: DocType = Field(default=DocType.GENERAL)
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    description: Optional[str] = None


class ReferenceDocumentUpdate(BaseModel):
    """更新参考文档请求"""
    name: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = None
    doc_type: Optional[DocType] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ReferenceDocumentResponse(BaseModel):
    """参考文档响应"""
    id: int
    name: str
    file_type: str
    file_size: int
    content: str
    doc_type: str
    source_lang: Optional[str]
    target_lang: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


class ReferenceDocumentListItem(BaseModel):
    """参考文档列表项（不包含内容）"""
    id: int
    name: str
    file_type: str
    file_size: int
    doc_type: str
    source_lang: Optional[str]
    target_lang: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


# ----- 文学翻译 Schemas -----

class LiteraryTranslationCreate(BaseModel):
    """创建文学翻译任务请求"""
    title: Optional[str] = None
    source_text: str = Field(..., min_length=1)
    source_lang: str = Field(..., min_length=1)
    target_lang: str = Field(..., min_length=1)
    literary_type: LiteraryType = Field(default=LiteraryType.GENERAL)
    reference_document_ids: Optional[List[int]] = Field(default=None)
    user_requirements: Optional[str] = Field(default=None, description="翻译需求说明（风格、术语等）")


class LiteraryParagraphResponse(BaseModel):
    """文学翻译段落响应"""
    id: int
    paragraph_index: int
    source_text: str
    translated_text: Optional[str]
    step1_translation: Optional[str]
    step2_verification: Optional[str]
    step3_revision: Optional[str]
    step4_finalization: Optional[str]
    user_edited_text: Optional[str]
    is_edited: bool
    beauty_sound_score: Optional[float]
    beauty_word_score: Optional[float]
    beauty_meaning_score: Optional[float]
    
    class Config:
        from_attributes = True


class LiteraryTranslationResponse(BaseModel):
    """文学翻译任务响应"""
    id: int
    title: Optional[str]
    source_text: str
    step1_translation: Optional[str]
    step2_verification: Optional[str]
    step3_revision: Optional[str]
    step4_finalization: Optional[str]
    final_translation: Optional[str]
    current_step: int
    status: str
    source_lang: str
    target_lang: str
    literary_type: str
    beauty_sound_score: Optional[float]
    beauty_word_score: Optional[float]
    beauty_meaning_score: Optional[float]
    ai_provider: Optional[str]
    ai_model: Optional[str]
    reference_document_ids: List[int]
    user_requirements: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    paragraphs: Optional[List[LiteraryParagraphResponse]] = None
    error_message: Optional[str] = None

    @field_serializer('created_at', 'updated_at', 'completed_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            # Windows 上某些日期值会触发 OSError，使用备用方案
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


class LiteraryTranslationListItem(BaseModel):
    """文学翻译任务列表项"""
    id: int
    title: Optional[str]
    status: str
    current_step: int
    error_message: Optional[str] = None
    source_lang: str
    target_lang: str
    literary_type: str
    beauty_sound_score: Optional[float]
    beauty_word_score: Optional[float]
    beauty_meaning_score: Optional[float]
    created_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, dt: datetime, _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            # Windows 上某些日期值会触发 OSError，使用备用方案
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


class ParagraphUpdateRequest(BaseModel):
    """更新段落译文请求"""
    user_edited_text: str = Field(..., min_length=0)


class LiteraryTranslationUpdate(BaseModel):
    """更新文学翻译任务请求"""
    title: Optional[str] = None
    source_text: Optional[str] = None
    final_translation: Optional[str] = None
    status: Optional[str] = None  # 状态管理：pending, translating, verifying, revising, finalizing, completed, failed


class WorkflowStepResponse(BaseModel):
    """工作流步骤响应"""
    step: int
    step_name: str
    status: str  # pending, processing, completed, failed
    result: Optional[str] = None
    analysis: Optional[str] = None  # AI 的分析说明
    

class LiteraryTranslationWorkflowResponse(BaseModel):
    """文学翻译工作流响应"""
    translation_id: int
    current_step: int
    overall_status: str
    steps: List[WorkflowStepResponse]
    paragraph_total: int = 0
    paragraph_done: int = 0


class ExportTranslationRequest(BaseModel):
    """导出翻译请求"""
    format: str = Field(default="txt", pattern="^(txt|md|html|json|csv)$")
    include_source: bool = Field(default=False, description="是否包含原文")


# ----- RAG 参考请求 Schemas -----

class RAGTranslationRequest(BaseModel):
    """带RAG的翻译请求"""
    text: str = Field(..., min_length=1)
    source_lang: str = Field(default="auto")
    target_lang: str = Field(...)
    reference_document_ids: Optional[List[int]] = Field(default=None)
    literary_type: LiteraryType = Field(default=LiteraryType.GENERAL)


# ============================================================
# 专业词库 Schemas
# ============================================================

class ProfessionalTermCreate(BaseModel):
    """创建专业词汇请求"""
    source_term: str = Field(..., min_length=1, max_length=500)
    target_term: str = Field(..., min_length=1, max_length=500)
    literary_type: LiteraryType = Field(default=LiteraryType.GENERAL)
    category: Optional[str] = Field(default=None, max_length=100)
    source_lang: str = Field(..., min_length=1)
    target_lang: str = Field(..., min_length=1)
    description: Optional[str] = None


class ProfessionalTermUpdate(BaseModel):
    """更新专业词汇请求"""
    target_term: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    is_verified: Optional[bool] = None


class ProfessionalTermResponse(BaseModel):
    """专业词汇响应"""
    id: int
    source_term: str
    target_term: str
    literary_type: str
    category: Optional[str]
    source_lang: str
    target_lang: str
    usage_count: int
    description: Optional[str]
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


class ProfessionalTermListRequest(BaseModel):
    """专业词汇列表查询请求"""
    literary_type: Optional[LiteraryType] = None
    category: Optional[str] = None
    source_lang: Optional[str] = None
    target_lang: Optional[str] = None
    keyword: Optional[str] = None
    is_verified: Optional[bool] = None


class TermItem(BaseModel):
    """词汇项"""
    source_term: str
    target_term: str
    category: Optional[str] = None
    description: Optional[str] = None


class TranslationTermSummaryResponse(BaseModel):
    """翻译任务专业词汇总结响应"""
    id: int
    translation_id: int
    terms: List[TermItem]
    total_terms: int
    new_terms: int
    updated_terms: int
    summary_text: Optional[str]
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        """安全序列化 datetime，避免 Windows 上的 OSError [Errno 22] Invalid argument"""
        if not dt:
            return None
        try:
            return dt.isoformat()
        except (OSError, ValueError):
            return dt.isoformat()[:19] if hasattr(dt, 'isoformat') else str(dt)

    class Config:
        from_attributes = True


class TermExtractionResult(BaseModel):
    """词汇提取结果"""
    terms: List[TermItem]
    summary: str
    total_count: int
