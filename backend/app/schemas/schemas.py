"""
Pydantic 数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


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
    status: str  # pending, completed, failed


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
    
    class Config:
        from_attributes = True


class LanguageInfo(BaseModel):
    """语言信息"""
    code: str
    name: str
