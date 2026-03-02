"""
数据模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


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
    items = Column(JSON, default=list)
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


# ============================================================
# 文学翻译全文翻译功能
# ============================================================

class LiteraryTranslationStatus(str, enum.Enum):
    """文学翻译任务状态"""
    PENDING = "pending"           # 待处理
    TRANSLATING = "translating"   # 翻译中
    VERIFYING = "verifying"       # 校验中
    REVISING = "revising"         # 修改中
    FINALIZING = "finalizing"     # 定稿中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败


class LiteraryTranslation(Base):
    """文学全文翻译任务"""
    __tablename__ = "literary_translations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=True, comment="文本标题")
    source_text = Column(Text, nullable=False, comment="原文")
    
    # 四步翻译结果
    step1_translation = Column(Text, nullable=True, comment="第一步：初译")
    step2_verification = Column(Text, nullable=True, comment="第二步：校验")
    step3_revision = Column(Text, nullable=True, comment="第三步：修改")
    step4_finalization = Column(Text, nullable=True, comment="第四步：定稿")
    
    # 当前步骤和状态
    current_step = Column(Integer, default=1, comment="当前步骤 1-4")
    status = Column(String(20), default=LiteraryTranslationStatus.PENDING, comment="任务状态")
    
    # 语言和配置
    source_lang = Column(String(10), nullable=False, comment="源语言")
    target_lang = Column(String(10), nullable=False, comment="目标语言")
    literary_type = Column(String(50), default="general", comment="文学类型: poetry, prose, novel, drama, general")
    
    # 三美原则评分
    beauty_sound_score = Column(Float, nullable=True, comment="音美评分 0-10")
    beauty_word_score = Column(Float, nullable=True, comment="词美评分 0-10")
    beauty_meaning_score = Column(Float, nullable=True, comment="意美评分 0-10")
    
    # AI 信息
    ai_provider = Column(String(50), nullable=True)
    ai_model = Column(String(100), nullable=True)
    
    # 参考文档关联
    reference_document_ids = Column(JSON, default=list, comment="关联的参考文档ID列表")
    
    # 用户翻译前指明的需求（风格、术语等）
    user_requirements = Column(Text, nullable=True, comment="用户翻译需求说明")
    
    # 用户编辑的最终译文
    final_translation = Column(Text, nullable=True, comment="用户编辑后的最终译文")
    
    # 工作流失败时记录的错误原因（便于排查）
    error_message = Column(Text, nullable=True, comment="翻译流程失败时的错误信息")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 关联段落
    paragraphs = relationship("LiteraryParagraph", back_populates="translation", cascade="all, delete-orphan")


class LiteraryParagraph(Base):
    """文学翻译段落（用于对照查看）"""
    __tablename__ = "literary_paragraphs"
    
    id = Column(Integer, primary_key=True, index=True)
    translation_id = Column(Integer, ForeignKey("literary_translations.id", ondelete="CASCADE"), nullable=False)
    paragraph_index = Column(Integer, nullable=False, comment="段落序号")
    
    source_text = Column(Text, nullable=False, comment="原文段落")
    translated_text = Column(Text, nullable=True, comment="译文段落")
    
    # 四步结果
    step1_translation = Column(Text, nullable=True)
    step2_verification = Column(Text, nullable=True)
    step3_revision = Column(Text, nullable=True)
    step4_finalization = Column(Text, nullable=True)
    
    # 用户编辑
    user_edited_text = Column(Text, nullable=True, comment="用户编辑的译文")
    is_edited = Column(Boolean, default=False)
    
    # 三美评分
    beauty_sound_score = Column(Float, nullable=True)
    beauty_word_score = Column(Float, nullable=True)
    beauty_meaning_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    translation = relationship("LiteraryTranslation", back_populates="paragraphs")


class ReferenceDocument(Base):
    """RAG 参考文档"""
    __tablename__ = "reference_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="文档名称")
    file_type = Column(String(50), nullable=False, comment="文件类型: txt, md, docx, pdf")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    
    # 文档内容
    content = Column(Text, nullable=False, comment="文档内容")
    
    # 文档类型
    doc_type = Column(String(50), default="general", comment="文档类型: terminology, style_guide, reference, general")
    
    # 语言对（如果是术语库或风格指南）
    source_lang = Column(String(10), nullable=True)
    target_lang = Column(String(10), nullable=True)
    
    # 描述
    description = Column(Text, nullable=True)
    
    # 是否启用
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================================
# 专业词库功能
# ============================================================

class ProfessionalTerm(Base):
    """专业词汇库"""
    __tablename__ = "professional_terms"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 词汇信息
    source_term = Column(String(500), nullable=False, comment="源语言词汇")
    target_term = Column(String(500), nullable=False, comment="目标语言翻译")
    
    # 分类信息
    literary_type = Column(String(50), nullable=False, comment="文学类型: poetry, prose, novel, drama, general")
    category = Column(String(100), nullable=True, comment="词汇分类/领域")
    
    # 语言对
    source_lang = Column(String(10), nullable=False)
    target_lang = Column(String(10), nullable=False)
    
    # 使用统计
    usage_count = Column(Integer, default=1, comment="使用次数")
    
    # 描述/例句
    description = Column(Text, nullable=True, comment="词汇说明/例句")
    
    # 关联的翻译任务
    translation_id = Column(Integer, ForeignKey("literary_translations.id"), nullable=True, comment="来源翻译任务")
    
    # 是否审核通过（防止错误词汇）
    is_verified = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 唯一约束：同类型、同语言对、同源词汇只能有一个
    __table_args__ = (
        # 使用Index来创建复合唯一约束
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class TranslationTermSummary(Base):
    """翻译任务专业词汇总结"""
    __tablename__ = "translation_term_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 关联的翻译任务
    translation_id = Column(Integer, ForeignKey("literary_translations.id", ondelete="CASCADE"), nullable=False)
    
    # 总结的词汇列表（JSON格式）
    terms = Column(JSON, default=list, comment="本次翻译涉及的专业词汇列表")
    
    # 词汇统计
    total_terms = Column(Integer, default=0, comment="词汇总数")
    new_terms = Column(Integer, default=0, comment="新增词汇数")
    updated_terms = Column(Integer, default=0, comment="更新词汇数")
    
    # AI总结说明
    summary_text = Column(Text, nullable=True, comment="AI对专业词汇的总结说明")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    translation = relationship("LiteraryTranslation")


class AIConfig(Base):
    """大模型配置（单行表，id 固定为 1）"""
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, default=1)
    provider = Column(String(50), nullable=False, default="deepseek", comment="AI 提供商: openai, deepseek, siliconflow, custom")
    api_key = Column(String(500), nullable=True, comment="API Key")
    model = Column(String(200), nullable=True, comment="模型名称")
    base_url = Column(String(500), nullable=True, comment="自定义 API 地址（custom 提供商时必填）")
    temperature = Column(Float, nullable=True, comment="温度参数")
    max_tokens = Column(Integer, nullable=True, comment="最大 token 数")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
