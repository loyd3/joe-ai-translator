"""
数据模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.sql import func
from app.database import Base


class TranslationHistory(Base):
    """翻译历史记录"""
    __tablename__ = "translation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    source_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    source_lang = Column(String(10), default="auto")
    target_lang = Column(String(10), nullable=False)
    context = Column(Text, nullable=True)
    ai_provider = Column(String(50), nullable=True)
    ai_model = Column(String(100), nullable=True)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BatchTranslation(Base):
    """批量翻译任务"""
    __tablename__ = "batch_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    source_lang = Column(String(10), default="auto")
    target_lang = Column(String(10), nullable=False)
    items = Column(JSON, default=list)  # 存储翻译项目列表
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
