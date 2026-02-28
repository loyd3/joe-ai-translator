"""
文学翻译 API 路由
支持全文翻译、四步翻译流程、RAG参考、对照编辑
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, AsyncGenerator
import json
import os
import io
import asyncio
from app.database import get_db
from app.schemas.schemas import (
    LiteraryTranslationCreate, LiteraryTranslationResponse,
    LiteraryTranslationListItem, LiteraryParagraphResponse,
    ParagraphUpdateRequest, LiteraryTranslationUpdate,
    ReferenceDocumentCreate, ReferenceDocumentResponse,
    ReferenceDocumentListItem, ReferenceDocumentUpdate,
    WorkflowStepResponse, LiteraryTranslationWorkflowResponse,
    ExportTranslationRequest,
    ProfessionalTermCreate, ProfessionalTermUpdate, ProfessionalTermResponse,
    TranslationTermSummaryResponse
)
from app.models.models import (
    LiteraryTranslation, LiteraryParagraph,
    ReferenceDocument, LiteraryTranslationStatus,
    ProfessionalTerm, TranslationTermSummary
)
from app.core.ai_client import get_ai_client

router = APIRouter(prefix="/api/literary", tags=["literary-translation"])


# ============================================================
# 参考文档管理
# ============================================================

@router.post("/references", response_model=ReferenceDocumentResponse)
async def create_reference_document(
    request: ReferenceDocumentCreate,
    db: Session = Depends(get_db)
):
    """创建参考文档"""
    doc = ReferenceDocument(
        name=request.name,
        file_type="txt",
        file_size=len(request.content.encode('utf-8')),
        content=request.content,
        doc_type=request.doc_type.value if hasattr(request.doc_type, 'value') else request.doc_type,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        description=request.description,
        is_active=True
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/references", response_model=List[ReferenceDocumentListItem])
async def list_reference_documents(
    doc_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取参考文档列表"""
    query = db.query(ReferenceDocument)
    if doc_type:
        query = query.filter(ReferenceDocument.doc_type == doc_type)
    if is_active is not None:
        query = query.filter(ReferenceDocument.is_active == is_active)
    query = query.order_by(ReferenceDocument.created_at.desc())
    return query.all()


@router.get("/references/{doc_id}", response_model=ReferenceDocumentResponse)
async def get_reference_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """获取参考文档详情"""
    doc = db.query(ReferenceDocument).filter(ReferenceDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Reference document not found")
    return doc


@router.put("/references/{doc_id}", response_model=ReferenceDocumentResponse)
async def update_reference_document(
    doc_id: int,
    request: ReferenceDocumentUpdate,
    db: Session = Depends(get_db)
):
    """更新参考文档"""
    doc = db.query(ReferenceDocument).filter(ReferenceDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Reference document not found")
    
    if request.name is not None:
        doc.name = request.name
    if request.content is not None:
        doc.content = request.content
        doc.file_size = len(request.content.encode('utf-8'))
    if request.doc_type is not None:
        doc.doc_type = request.doc_type.value if hasattr(request.doc_type, 'value') else request.doc_type
    if request.description is not None:
        doc.description = request.description
    if request.is_active is not None:
        doc.is_active = request.is_active
    
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/references/{doc_id}")
async def delete_reference_document(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """删除参考文档"""
    doc = db.query(ReferenceDocument).filter(ReferenceDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Reference document not found")
    
    db.delete(doc)
    db.commit()
    return {"message": "Reference document deleted successfully"}


@router.post("/references/upload")
async def upload_reference_document(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    source_lang: Optional[str] = Form(None),
    target_lang: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """上传参考文档文件"""
    # 读取文件内容
    content = await file.read()
    text_content = content.decode('utf-8')
    
    doc = ReferenceDocument(
        name=file.filename,
        file_type=file.filename.split('.')[-1] if '.' in file.filename else 'txt',
        file_size=len(content),
        content=text_content,
        doc_type=doc_type,
        source_lang=source_lang,
        target_lang=target_lang,
        description=description,
        is_active=True
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ============================================================
# 文学翻译任务管理
# ============================================================

def split_text_into_paragraphs(text: str) -> List[str]:
    """将文本分割成段落"""
    # 按空行分割，保留非空段落
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        # 如果没有空行，按换行分割
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    return paragraphs


def get_reference_content(doc_ids: List[int], db: Session) -> str:
    """获取参考文档内容"""
    if not doc_ids:
        return ""
    
    docs = db.query(ReferenceDocument).filter(
        ReferenceDocument.id.in_(doc_ids),
        ReferenceDocument.is_active == True
    ).all()
    
    contents = []
    for doc in docs:
        contents.append(f"=== {doc.name} ({doc.doc_type}) ===\n{doc.content}\n")
    
    return "\n".join(contents)


def get_reference_and_requirements(translation: LiteraryTranslation, db: Session) -> str:
    """参考文档 + 用户翻译需求，供 AI 提示使用"""
    ref = get_reference_content(translation.reference_document_ids or [], db)
    if translation.user_requirements and translation.user_requirements.strip():
        req = f"\n\n## 用户翻译需求\n{translation.user_requirements.strip()}"
        ref = (ref + req) if ref else req.lstrip()
    return ref or ""


@router.post("/translations", response_model=LiteraryTranslationResponse)
async def create_literary_translation(
    request: LiteraryTranslationCreate,
    db: Session = Depends(get_db)
):
    """创建文学翻译任务"""
    # 创建翻译任务
    translation = LiteraryTranslation(
        title=request.title,
        source_text=request.source_text,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        literary_type=request.literary_type.value if hasattr(request.literary_type, 'value') else request.literary_type,
        reference_document_ids=request.reference_document_ids or [],
        user_requirements=request.user_requirements,
        status=LiteraryTranslationStatus.PENDING,
        current_step=1
    )
    db.add(translation)
    db.commit()
    db.refresh(translation)
    
    # 分割段落
    paragraphs = split_text_into_paragraphs(request.source_text)
    
    for idx, para_text in enumerate(paragraphs):
        paragraph = LiteraryParagraph(
            translation_id=translation.id,
            paragraph_index=idx,
            source_text=para_text
        )
        db.add(paragraph)
    
    db.commit()
    
    # 刷新并返回完整数据
    db.refresh(translation)
    return translation


@router.get("/translations", response_model=List[LiteraryTranslationListItem])
async def list_literary_translations(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取文学翻译任务列表"""
    query = db.query(LiteraryTranslation)
    if status:
        query = query.filter(LiteraryTranslation.status == status)
    query = query.order_by(LiteraryTranslation.created_at.desc())
    return query.offset(skip).limit(limit).all()


@router.get("/translations/{translation_id}", response_model=LiteraryTranslationResponse)
async def get_literary_translation(
    translation_id: int,
    include_paragraphs: bool = True,
    db: Session = Depends(get_db)
):
    """获取文学翻译任务详情"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    return translation


@router.put("/translations/{translation_id}", response_model=LiteraryTranslationResponse)
async def update_literary_translation(
    translation_id: int,
    request: LiteraryTranslationUpdate,
    db: Session = Depends(get_db)
):
    """更新文学翻译任务"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    if request.title is not None:
        translation.title = request.title
    if request.final_translation is not None:
        translation.final_translation = request.final_translation
    
    db.commit()
    db.refresh(translation)
    return translation


@router.delete("/translations/{translation_id}")
async def delete_literary_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """删除文学翻译任务"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    db.delete(translation)
    db.commit()
    return {"message": "Translation deleted successfully"}


# ============================================================
# 四步翻译流程 API（内部执行函数供 run_all 复用）
# ============================================================

async def _execute_step1(translation_id: int, db: Session) -> None:
    """执行第一步：初译"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    translation.status = LiteraryTranslationStatus.TRANSLATING
    db.commit()
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    reference_content = get_reference_and_requirements(translation, db)
    full_step1 = []
    for para in paragraphs:
        result = await client.literary_translate(
            para.source_text, translation.source_lang, translation.target_lang,
            translation.literary_type, reference_content
        )
        para.step1_translation = result
        para.translated_text = result
        full_step1.append(result)
    translation.step1_translation = "\n\n".join(full_step1)
    translation.current_step = 2
    translation.status = LiteraryTranslationStatus.VERIFYING
    db.commit()


async def _execute_step2(translation_id: int, db: Session) -> None:
    """执行第二步：校验"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation or translation.current_step < 2:
        raise HTTPException(status_code=400, detail="Please complete step 1 first")
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    full_step2 = []
    total_sound, total_word, total_meaning = 0, 0, 0
    for para in paragraphs:
        result = await client.literary_verify(
            para.source_text, para.step1_translation or para.translated_text or "",
            translation.source_lang, translation.target_lang, translation.literary_type
        )
        verified = result.get("verified_translation", para.step1_translation)
        para.step2_verification = verified
        para.translated_text = verified
        para.beauty_sound_score = result.get("beauty_sound_score", 7.0)
        para.beauty_word_score = result.get("beauty_word_score", 7.0)
        para.beauty_meaning_score = result.get("beauty_meaning_score", 7.0)
        total_sound += para.beauty_sound_score
        total_word += para.beauty_word_score
        total_meaning += para.beauty_meaning_score
        full_step2.append(verified)
    translation.step2_verification = "\n\n".join(full_step2)
    translation.current_step = 3
    translation.status = LiteraryTranslationStatus.REVISING
    if paragraphs:
        translation.beauty_sound_score = total_sound / len(paragraphs)
        translation.beauty_word_score = total_word / len(paragraphs)
        translation.beauty_meaning_score = total_meaning / len(paragraphs)
    db.commit()


async def _execute_step3(translation_id: int, db: Session) -> None:
    """执行第三步：修改"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation or translation.current_step < 3:
        raise HTTPException(status_code=400, detail="Please complete step 2 first")
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    full_step3 = []
    for para in paragraphs:
        verification_analysis = {
            "issues_found": [], "suggestions": [],
            "beauty_sound_score": para.beauty_sound_score,
            "beauty_word_score": para.beauty_word_score,
            "beauty_meaning_score": para.beauty_meaning_score,
        }
        result = await client.literary_revise(
            para.source_text, para.step2_verification or para.translated_text or "",
            verification_analysis, translation.source_lang, translation.target_lang, translation.literary_type
        )
        revised = result.get("revised_translation", para.step2_verification)
        para.step3_revision = revised
        para.translated_text = revised
        full_step3.append(revised)
    translation.step3_revision = "\n\n".join(full_step3)
    translation.current_step = 4
    translation.status = LiteraryTranslationStatus.FINALIZING
    db.commit()


async def _execute_step4(translation_id: int, db: Session) -> None:
    """执行第四步：定稿"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation or translation.current_step < 4:
        raise HTTPException(status_code=400, detail="Please complete step 3 first")
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    full_step4 = []
    for para in paragraphs:
        result = await client.literary_finalize(
            para.source_text, para.step3_revision or para.translated_text or "",
            translation.source_lang, translation.target_lang, translation.literary_type
        )
        finalized = result.get("final_translation", para.step3_revision)
        para.step4_finalization = finalized
        para.translated_text = finalized
        full_step4.append(finalized)
    translation.step4_finalization = "\n\n".join(full_step4)
    translation.final_translation = "\n\n".join(full_step4)
    translation.current_step = 4
    translation.status = LiteraryTranslationStatus.COMPLETED
    from datetime import datetime
    translation.completed_at = datetime.now()
    db.commit()
    try:
        await auto_extract_terms_after_finalize(translation_id, db)
    except Exception as e:
        print(f"[Auto Extract Terms] Error: {e}")


@router.post("/translations/{translation_id}/workflow/start")
async def start_translation_workflow(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """开始四步翻译流程（第一步：初译）"""
    await _execute_step1(translation_id, db)
    return {"message": "Step 1 (Translation) completed", "current_step": 2}


@router.post("/translations/{translation_id}/workflow/verify")
async def verify_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """执行第二步：校验"""
    await _execute_step2(translation_id, db)
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    return {
        "message": "Step 2 (Verification) completed",
        "current_step": 3,
        "beauty_scores": {
            "sound": translation.beauty_sound_score,
            "word": translation.beauty_word_score,
            "meaning": translation.beauty_meaning_score
        }
    }


@router.post("/translations/{translation_id}/workflow/revise")
async def revise_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """执行第三步：修改"""
    await _execute_step3(translation_id, db)
    return {"message": "Step 3 (Revision) completed", "current_step": 4}


@router.post("/translations/{translation_id}/workflow/finalize")
async def finalize_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """执行第四步：定稿"""
    await _execute_step4(translation_id, db)
    return {"message": "Step 4 (Finalization) completed. Translation finished!", "current_step": 4}


@router.post("/translations/{translation_id}/workflow/run-all")
async def run_all_workflow_steps(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """一键自动执行四步流程：初译 → 校验 → 修改 → 定稿"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    await _execute_step1(translation_id, db)
    await _execute_step2(translation_id, db)
    await _execute_step3(translation_id, db)
    await _execute_step4(translation_id, db)
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    return {
        "message": "四步流程已全部完成",
        "current_step": 4,
        "status": translation.status,
        "beauty_scores": {
            "sound": translation.beauty_sound_score,
            "word": translation.beauty_word_score,
            "meaning": translation.beauty_meaning_score
        }
    }


@router.get("/translations/{translation_id}/workflow", response_model=LiteraryTranslationWorkflowResponse)
async def get_workflow_status(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """获取工作流状态"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    steps = [
        WorkflowStepResponse(
            step=1,
            step_name="翻译",
            status="completed" if translation.step1_translation else "pending",
            result=translation.step1_translation[:200] + "..." if translation.step1_translation and len(translation.step1_translation) > 200 else translation.step1_translation
        ),
        WorkflowStepResponse(
            step=2,
            step_name="校验",
            status="completed" if translation.step2_verification else ("pending" if translation.current_step < 2 else "processing"),
            result=translation.step2_verification[:200] + "..." if translation.step2_verification and len(translation.step2_verification) > 200 else translation.step2_verification
        ),
        WorkflowStepResponse(
            step=3,
            step_name="修改",
            status="completed" if translation.step3_revision else ("pending" if translation.current_step < 3 else "processing"),
            result=translation.step3_revision[:200] + "..." if translation.step3_revision and len(translation.step3_revision) > 200 else translation.step3_revision
        ),
        WorkflowStepResponse(
            step=4,
            step_name="定稿",
            status="completed" if translation.step4_finalization else ("pending" if translation.current_step < 4 else "processing"),
            result=translation.step4_finalization[:200] + "..." if translation.step4_finalization and len(translation.step4_finalization) > 200 else translation.step4_finalization
        ),
    ]
    
    return LiteraryTranslationWorkflowResponse(
        translation_id=translation_id,
        current_step=translation.current_step,
        overall_status=translation.status,
        steps=steps
    )


# ============================================================
# 段落管理
# ============================================================

@router.get("/translations/{translation_id}/paragraphs", response_model=List[LiteraryParagraphResponse])
async def get_paragraphs(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """获取所有段落"""
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    return paragraphs


@router.put("/paragraphs/{paragraph_id}", response_model=LiteraryParagraphResponse)
async def update_paragraph(
    paragraph_id: int,
    request: ParagraphUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新段落译文（用户编辑）"""
    paragraph = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.id == paragraph_id
    ).first()
    
    if not paragraph:
        raise HTTPException(status_code=404, detail="Paragraph not found")
    
    paragraph.user_edited_text = request.user_edited_text
    paragraph.translated_text = request.user_edited_text
    paragraph.is_edited = True
    
    db.commit()
    db.refresh(paragraph)
    
    # 更新全文
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == paragraph.translation_id
    ).first()
    
    if translation:
        all_paras = db.query(LiteraryParagraph).filter(
            LiteraryParagraph.translation_id == translation.id
        ).order_by(LiteraryParagraph.paragraph_index).all()
        
        translation.final_translation = "\n\n".join([
            p.user_edited_text or p.translated_text or "" for p in all_paras
        ])
        db.commit()
    
    return paragraph


# ============================================================
# 导出功能 - 支持多种格式
# ============================================================

def generate_txt_content(translation, paragraphs, include_source: bool = False) -> str:
    """生成纯文本格式内容"""
    lines = []
    
    if translation.title:
        lines.append(f"{translation.title}")
        lines.append("=" * 50)
        lines.append("")
    
    lines.append(f"原文语言: {translation.source_lang}")
    lines.append(f"译文语言: {translation.target_lang}")
    lines.append(f"文学类型: {translation.literary_type}")
    lines.append(f"生成时间: {translation.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    if translation.beauty_sound_score:
        lines.append(f"音美评分: {translation.beauty_sound_score:.1f}/10")
        lines.append(f"词美评分: {translation.beauty_word_score:.1f}/10")
        lines.append(f"意美评分: {translation.beauty_meaning_score:.1f}/10")
        lines.append("")
    
    lines.append("=" * 50)
    lines.append("")
    
    for i, para in enumerate(paragraphs, 1):
        if include_source:
            lines.append(f"【原文 {i}】")
            lines.append(para.source_text)
            lines.append("")
            lines.append(f"【译文 {i}】")
        
        text = para.user_edited_text or para.translated_text or ""
        lines.append(text)
        lines.append("")
    
    return "\n".join(lines)


def generate_md_content(translation, paragraphs, include_source: bool = False) -> str:
    """生成 Markdown 格式内容"""
    lines = []
    
    if translation.title:
        lines.append(f"# {translation.title}")
        lines.append("")
    else:
        lines.append("# 文学翻译结果")
        lines.append("")
    
    lines.append("## 翻译信息")
    lines.append("")
    lines.append(f"- **原文语言**: {translation.source_lang}")
    lines.append(f"- **译文语言**: {translation.target_lang}")
    lines.append(f"- **文学类型**: {translation.literary_type}")
    lines.append(f"- **生成时间**: {translation.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    if translation.beauty_sound_score:
        lines.append("## 三美评分")
        lines.append("")
        lines.append(f"- **音美**: {translation.beauty_sound_score:.1f}/10")
        lines.append(f"- **词美**: {translation.beauty_word_score:.1f}/10")
        lines.append(f"- **意美**: {translation.beauty_meaning_score:.1f}/10")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## 翻译内容")
    lines.append("")
    
    for i, para in enumerate(paragraphs, 1):
        if include_source:
            lines.append(f"### 段落 {i}")
            lines.append("")
            lines.append("**原文：**")
            lines.append("")
            lines.append(f"> {para.source_text}")
            lines.append("")
            lines.append("**译文：**")
            lines.append("")
        
        text = para.user_edited_text or para.translated_text or ""
        lines.append(text)
        lines.append("")
        if include_source:
            lines.append("---")
            lines.append("")
    
    return "\n".join(lines)


def generate_html_content(translation, paragraphs, include_source: bool = False) -> str:
    """生成 HTML 格式内容"""
    html_parts = []
    
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html lang=\"zh-CN\">")
    html_parts.append("<head>")
    html_parts.append("<meta charset=\"UTF-8\">")
    html_parts.append(f"<title>{translation.title or '文学翻译结果'}</title>")
    html_parts.append("<style>")
    html_parts.append("""
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 40px 20px; line-height: 1.8; color: #333; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .info-box { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .scores { display: flex; gap: 20px; margin: 10px 0; }
        .score-item { background: #e8f4f8; padding: 10px 20px; border-radius: 6px; }
        .paragraph { margin: 30px 0; padding: 20px; background: #fff; border: 1px solid #e1e8ed; border-radius: 8px; }
        .source { color: #666; font-style: italic; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px dashed #ddd; }
        .translation { color: #2c3e50; font-size: 1.1em; }
        .para-num { color: #3498db; font-weight: bold; margin-bottom: 10px; }
        hr { border: none; border-top: 2px solid #ecf0f1; margin: 30px 0; }
    """)
    html_parts.append("</style>")
    html_parts.append("</head>")
    html_parts.append("<body>")
    
    # 标题
    html_parts.append(f"<h1>{translation.title or '文学翻译结果'}</h1>")
    
    # 信息区域
    html_parts.append("<div class='info-box'>")
    html_parts.append(f"<p><strong>原文语言：</strong>{translation.source_lang}</p>")
    html_parts.append(f"<p><strong>译文语言：</strong>{translation.target_lang}</p>")
    html_parts.append(f"<p><strong>文学类型：</strong>{translation.literary_type}</p>")
    html_parts.append(f"<p><strong>生成时间：</strong>{translation.created_at.strftime('%Y-%m-%d %H:%M')}</p>")
    
    if translation.beauty_sound_score:
        html_parts.append("<div class='scores'>")
        html_parts.append(f"<div class='score-item'><strong>音美:</strong> {translation.beauty_sound_score:.1f}/10</div>")
        html_parts.append(f"<div class='score-item'><strong>词美:</strong> {translation.beauty_word_score:.1f}/10</div>")
        html_parts.append(f"<div class='score-item'><strong>意美:</strong> {translation.beauty_meaning_score:.1f}/10</div>")
        html_parts.append("</div>")
    
    html_parts.append("</div>")
    html_parts.append("<hr>")
    
    # 内容区域
    for i, para in enumerate(paragraphs, 1):
        html_parts.append("<div class='paragraph'>")
        html_parts.append(f"<div class='para-num'>段落 {i}</div>")
        
        if include_source:
            html_parts.append(f"<div class='source'>{para.source_text}</div>")
        
        text = para.user_edited_text or para.translated_text or ""
        # 处理换行
        text_html = text.replace("\n", "<br>")
        html_parts.append(f"<div class='translation'>{text_html}</div>")
        html_parts.append("</div>")
    
    html_parts.append("</body>")
    html_parts.append("</html>")
    
    return "\n".join(html_parts)


def generate_json_content(translation, paragraphs, include_source: bool = False) -> str:
    """生成 JSON 格式内容"""
    import json
    
    data = {
        "title": translation.title,
        "source_lang": translation.source_lang,
        "target_lang": translation.target_lang,
        "literary_type": translation.literary_type,
        "created_at": translation.created_at.isoformat() if translation.created_at else None,
        "beauty_scores": {
            "sound": float(translation.beauty_sound_score) if translation.beauty_sound_score else None,
            "word": float(translation.beauty_word_score) if translation.beauty_word_score else None,
            "meaning": float(translation.beauty_meaning_score) if translation.beauty_meaning_score else None
        } if translation.beauty_sound_score else None,
        "paragraphs": []
    }
    
    for i, para in enumerate(paragraphs, 1):
        para_data = {
            "index": i,
            "translation": para.user_edited_text or para.translated_text or ""
        }
        if include_source:
            para_data["source"] = para.source_text
        data["paragraphs"].append(para_data)
    
    return json.dumps(data, ensure_ascii=False, indent=2)


def generate_csv_content(translation, paragraphs, include_source: bool = False) -> str:
    """生成 CSV 格式内容"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入头部信息
    writer.writerow(["文学翻译结果"])
    writer.writerow(["标题", translation.title or ""])
    writer.writerow(["原文语言", translation.source_lang])
    writer.writerow(["译文语言", translation.target_lang])
    writer.writerow(["文学类型", translation.literary_type])
    writer.writerow(["生成时间", translation.created_at.strftime('%Y-%m-%d %H:%M') if translation.created_at else ""])
    
    if translation.beauty_sound_score:
        writer.writerow(["音美评分", f"{translation.beauty_sound_score:.1f}"])
        writer.writerow(["词美评分", f"{translation.beauty_word_score:.1f}"])
        writer.writerow(["意美评分", f"{translation.beauty_meaning_score:.1f}"])
    
    writer.writerow([])  # 空行
    
    # 写入段落内容
    if include_source:
        writer.writerow(["段落编号", "原文", "译文"])
        for i, para in enumerate(paragraphs, 1):
            text = para.user_edited_text or para.translated_text or ""
            writer.writerow([i, para.source_text, text])
    else:
        writer.writerow(["段落编号", "译文"])
        for i, para in enumerate(paragraphs, 1):
            text = para.user_edited_text or para.translated_text or ""
            writer.writerow([i, text])
    
    return output.getvalue()


@router.post("/translations/{translation_id}/export")
async def export_translation(
    translation_id: int,
    request: ExportTranslationRequest,
    db: Session = Depends(get_db)
):
    """导出翻译结果 - 支持多种格式: txt, md, html, json, csv"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    format_generators = {
        "txt": generate_txt_content,
        "md": generate_md_content,
        "html": generate_html_content,
        "json": generate_json_content,
        "csv": generate_csv_content,
    }
    
    format_mime_types = {
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "html": "text/html; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "csv": "text/csv; charset=utf-8",
    }
    
    format_ext = request.format.lower()
    
    if format_ext not in format_generators:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的格式: {request.format}. 支持的格式: {', '.join(format_generators.keys())}"
        )
    
    # 生成内容
    content = format_generators[format_ext](
        translation,
        paragraphs,
        request.include_source
    )

    return {
        "filename": f"literary_translation_{translation_id}.{format_ext}",
        "content": content,
        "format": request.format,
        "mime_type": format_mime_types[format_ext]
    }


# ============================================================
# 专业词库管理
# ============================================================

@router.get("/terms", response_model=List[ProfessionalTermResponse])
async def list_professional_terms(
    literary_type: Optional[str] = None,
    category: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    keyword: Optional[str] = None,
    is_verified: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取专业词汇列表"""
    query = db.query(ProfessionalTerm)

    if literary_type:
        query = query.filter(ProfessionalTerm.literary_type == literary_type)
    if category:
        query = query.filter(ProfessionalTerm.category == category)
    if source_lang:
        query = query.filter(ProfessionalTerm.source_lang == source_lang)
    if target_lang:
        query = query.filter(ProfessionalTerm.target_lang == target_lang)
    if is_verified is not None:
        query = query.filter(ProfessionalTerm.is_verified == is_verified)
    if keyword:
        query = query.filter(
            (ProfessionalTerm.source_term.contains(keyword)) |
            (ProfessionalTerm.target_term.contains(keyword))
        )

    query = query.order_by(ProfessionalTerm.usage_count.desc(), ProfessionalTerm.created_at.desc())
    return query.offset(skip).limit(limit).all()


@router.post("/terms", response_model=ProfessionalTermResponse)
async def create_professional_term(
    request: ProfessionalTermCreate,
    db: Session = Depends(get_db)
):
    """创建专业词汇"""
    # 检查是否已存在相同词汇
    existing = db.query(ProfessionalTerm).filter(
        ProfessionalTerm.source_term == request.source_term,
        ProfessionalTerm.literary_type == request.literary_type,
        ProfessionalTerm.source_lang == request.source_lang,
        ProfessionalTerm.target_lang == request.target_lang
    ).first()

    if existing:
        # 更新现有词汇
        existing.target_term = request.target_term
        existing.category = request.category
        existing.description = request.description
        existing.usage_count += 1
        db.commit()
        db.refresh(existing)
        return existing

    # 创建新词汇
    term = ProfessionalTerm(
        source_term=request.source_term,
        target_term=request.target_term,
        literary_type=request.literary_type.value if hasattr(request.literary_type, 'value') else request.literary_type,
        category=request.category,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        description=request.description,
        usage_count=1,
        is_verified=True
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return term


@router.put("/terms/{term_id}", response_model=ProfessionalTermResponse)
async def update_professional_term(
    term_id: int,
    request: ProfessionalTermUpdate,
    db: Session = Depends(get_db)
):
    """更新专业词汇"""
    term = db.query(ProfessionalTerm).filter(ProfessionalTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    if request.target_term is not None:
        term.target_term = request.target_term
    if request.category is not None:
        term.category = request.category
    if request.description is not None:
        term.description = request.description
    if request.is_verified is not None:
        term.is_verified = request.is_verified

    db.commit()
    db.refresh(term)
    return term


@router.delete("/terms/{term_id}")
async def delete_professional_term(
    term_id: int,
    db: Session = Depends(get_db)
):
    """删除专业词汇"""
    term = db.query(ProfessionalTerm).filter(ProfessionalTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    db.delete(term)
    db.commit()
    return {"message": "Term deleted successfully"}


@router.get("/terms/categories")
async def get_term_categories(
    literary_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取词汇分类列表"""
    query = db.query(ProfessionalTerm.category).distinct()
    if literary_type:
        query = query.filter(ProfessionalTerm.literary_type == literary_type)

    categories = [c[0] for c in query.all() if c[0]]
    return categories


# ============================================================
# 翻译词汇总结
# ============================================================

@router.get("/translations/{translation_id}/terms", response_model=TranslationTermSummaryResponse)
async def get_translation_term_summary(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """获取翻译任务的专业词汇总结"""
    summary = db.query(TranslationTermSummary).filter(
        TranslationTermSummary.translation_id == translation_id
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="Term summary not found")

    return summary


@router.post("/translations/{translation_id}/terms/extract")
async def extract_terms_from_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """从翻译任务中提取专业词汇"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()

    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    # 获取该类型的已有词汇
    existing_terms = db.query(ProfessionalTerm).filter(
        ProfessionalTerm.literary_type == translation.literary_type,
        ProfessionalTerm.source_lang == translation.source_lang,
        ProfessionalTerm.target_lang == translation.target_lang
    ).all()

    existing_terms_list = [
        {"source_term": t.source_term, "target_term": t.target_term}
        for t in existing_terms
    ]

    # 使用 AI 提取词汇
    client = get_ai_client()
    result = await client.extract_professional_terms(
        source_text=translation.source_text,
        translated_text=translation.final_translation or translation.step4_finalization or "",
        source_lang=translation.source_lang,
        target_lang=translation.target_lang,
        literary_type=translation.literary_type,
        existing_terms=existing_terms_list
    )

    # 处理提取的词汇
    new_count = 0
    updated_count = 0
    terms_for_summary = []

    for term_data in result.get("terms", []):
        source_term = term_data.get("source_term", "")
        target_term = term_data.get("target_term", "")
        category = term_data.get("category", "")
        description = term_data.get("description", "")

        if not source_term or not target_term:
            continue

        terms_for_summary.append({
            "source_term": source_term,
            "target_term": target_term,
            "category": category,
            "description": description
        })

        # 检查是否已存在
        existing = db.query(ProfessionalTerm).filter(
            ProfessionalTerm.source_term == source_term,
            ProfessionalTerm.literary_type == translation.literary_type,
            ProfessionalTerm.source_lang == translation.source_lang,
            ProfessionalTerm.target_lang == translation.target_lang
        ).first()

        if existing:
            # 更新现有词汇
            existing.target_term = target_term
            existing.category = category
            existing.description = description
            existing.usage_count += 1
            updated_count += 1
        else:
            # 创建新词汇
            new_term = ProfessionalTerm(
                source_term=source_term,
                target_term=target_term,
                literary_type=translation.literary_type,
                category=category,
                source_lang=translation.source_lang,
                target_lang=translation.target_lang,
                description=description,
                usage_count=1,
                translation_id=translation_id,
                is_verified=True
            )
            db.add(new_term)
            new_count += 1

    db.commit()

    # 创建总结记录
    summary = TranslationTermSummary(
        translation_id=translation_id,
        terms=terms_for_summary,
        total_terms=len(terms_for_summary),
        new_terms=new_count,
        updated_terms=updated_count,
        summary_text=result.get("summary", "")
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    return {
        "message": f"提取完成，新增 {new_count} 个词汇，更新 {updated_count} 个词汇",
        "summary": summary
    }


# ============================================================
# 辅助函数：定稿时自动提取词汇
# ============================================================

async def auto_extract_terms_after_finalize(
    translation_id: int,
    db: Session
):
    """定稿后自动提取专业词汇"""
    try:
        translation = db.query(LiteraryTranslation).filter(
            LiteraryTranslation.id == translation_id
        ).first()

        if not translation or not (translation.final_translation or translation.step4_finalization):
            return

        # 获取该类型的已有词汇
        existing_terms = db.query(ProfessionalTerm).filter(
            ProfessionalTerm.literary_type == translation.literary_type,
            ProfessionalTerm.source_lang == translation.source_lang,
            ProfessionalTerm.target_lang == translation.target_lang
        ).all()

        existing_terms_list = [
            {"source_term": t.source_term, "target_term": t.target_term}
            for t in existing_terms
        ]

        # 使用 AI 提取词汇
        client = get_ai_client()
        result = await client.extract_professional_terms(
            source_text=translation.source_text,
            translated_text=translation.final_translation or translation.step4_finalization,
            source_lang=translation.source_lang,
            target_lang=translation.target_lang,
            literary_type=translation.literary_type,
            existing_terms=existing_terms_list
        )

        # 处理提取的词汇
        new_count = 0
        updated_count = 0
        terms_for_summary = []

        for term_data in result.get("terms", []):
            source_term = term_data.get("source_term", "")
            target_term = term_data.get("target_term", "")
            category = term_data.get("category", "")
            description = term_data.get("description", "")

            if not source_term or not target_term:
                continue

            terms_for_summary.append({
                "source_term": source_term,
                "target_term": target_term,
                "category": category,
                "description": description
            })

            # 检查是否已存在
            existing = db.query(ProfessionalTerm).filter(
                ProfessionalTerm.source_term == source_term,
                ProfessionalTerm.literary_type == translation.literary_type,
                ProfessionalTerm.source_lang == translation.source_lang,
                ProfessionalTerm.target_lang == translation.target_lang
            ).first()

            if existing:
                existing.target_term = target_term
                existing.category = category
                existing.description = description
                existing.usage_count += 1
                updated_count += 1
            else:
                new_term = ProfessionalTerm(
                    source_term=source_term,
                    target_term=target_term,
                    literary_type=translation.literary_type,
                    category=category,
                    source_lang=translation.source_lang,
                    target_lang=translation.target_lang,
                    description=description,
                    usage_count=1,
                    translation_id=translation_id,
                    is_verified=True
                )
                db.add(new_term)
                new_count += 1

        db.commit()

        # 创建总结记录
        summary = TranslationTermSummary(
            translation_id=translation_id,
            terms=terms_for_summary,
            total_terms=len(terms_for_summary),
            new_terms=new_count,
            updated_terms=updated_count,
            summary_text=result.get("summary", "")
        )
        db.add(summary)
        db.commit()

    except Exception as e:
        print(f"[Auto Extract Terms] Error: {e}")
        # 不抛出异常，避免影响定稿流程


# ============================================================
# 长文件一键翻译
# ============================================================

def parse_text_file(content: bytes, file_type: str) -> str:
    """解析文本文件内容"""
    try:
        if file_type in ['txt', 'md']:
            return content.decode('utf-8')
        elif file_type == 'docx':
            # 简化处理，实际应该使用 python-docx
            return content.decode('utf-8', errors='ignore')
        else:
            return content.decode('utf-8', errors='ignore')
    except Exception as e:
        raise ValueError(f"无法解析文件: {str(e)}")


def split_long_text(text: str, max_chunk_size: int = 2000) -> List[str]:
    """
    将长文本分段，每段不超过 max_chunk_size 字符
    尽量在段落边界处分割
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    # 先按段落分割
    paragraphs = text.split('\n\n')
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        para_size = len(para) + 2  # +2 for '\n\n'
        
        if current_size + para_size > max_chunk_size and current_chunk:
            # 保存当前块
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = len(para)
        else:
            current_chunk.append(para)
            current_size += para_size
    
    # 添加最后一块
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks


@router.post("/translations/upload")
async def upload_and_translate_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source_lang: str = Form("auto"),
    target_lang: str = Form("en"),
    literary_type: str = Form("general"),
    reference_document_ids: Optional[str] = Form(None),
    user_requirements: Optional[str] = Form(None),
    auto_run: bool = Form(True, description="是否自动执行四步流程"),
    db: Session = Depends(get_db)
):
    """
    上传文件并创建翻译任务，支持 txt、md；可选自动执行四步流程。
    """
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ['txt', 'md']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_extension}. 支持: txt, md"
        )
    content = await file.read()
    try:
        text_content = parse_text_file(content, file_extension)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")
    ref_ids = json.loads(reference_document_ids) if reference_document_ids else []
    translation = LiteraryTranslation(
        title=title or file.filename,
        source_text=text_content,
        source_lang=source_lang,
        target_lang=target_lang,
        literary_type=literary_type,
        reference_document_ids=ref_ids,
        user_requirements=user_requirements.strip() if user_requirements else None,
        status=LiteraryTranslationStatus.PENDING,
        current_step=1
    )
    db.add(translation)
    db.commit()
    db.refresh(translation)
    chunks = split_long_text(text_content)
    for idx, chunk in enumerate(chunks):
        paragraph = LiteraryParagraph(
            translation_id=translation.id,
            paragraph_index=idx,
            source_text=chunk
        )
        db.add(paragraph)
    db.commit()
    if auto_run:
        try:
            await _execute_step1(translation.id, db)
            await _execute_step2(translation.id, db)
            await _execute_step3(translation.id, db)
            await _execute_step4(translation.id, db)
            db.refresh(translation)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"自动执行四步流程失败: {str(e)}")
    return {
        "message": "文件上传成功" + ("，四步流程已自动执行完成" if auto_run else "，翻译任务已创建"),
        "translation_id": translation.id,
        "filename": file.filename,
        "total_chunks": len(chunks),
        "total_chars": len(text_content),
        "current_step": translation.current_step,
        "status": translation.status
    }


@router.post("/translations/{translation_id}/translate-all")
async def translate_all_chunks(
    translation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    一键翻译所有段落（长文本批量翻译）
    """
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    if not paragraphs:
        raise HTTPException(status_code=400, detail="没有需要翻译的段落")
    
    # 更新状态为翻译中
    translation.status = LiteraryTranslationStatus.TRANSLATING
    db.commit()
    
    client = get_ai_client()
    
    # 获取参考文档内容
    reference_content = ""
    if translation.reference_document_ids:
        docs = db.query(ReferenceDocument).filter(
            ReferenceDocument.id.in_(translation.reference_document_ids),
            ReferenceDocument.is_active == True
        ).all()
        reference_content = "\n\n".join([f"=== {d.name} ===\n{d.content}" for d in docs])
    
    # 批量翻译所有段落
    total = len(paragraphs)
    success_count = 0
    
    for idx, para in enumerate(paragraphs):
        try:
            result = await client.literary_translate_paragraph(
                paragraph=para.source_text,
                source_lang=translation.source_lang,
                target_lang=translation.target_lang,
                literary_type=translation.literary_type,
                reference_content=reference_content if reference_content else None
            )
            
            # 保存四步翻译结果
            para.step1_translation = result["step1_translation"]
            para.step2_verification = result["step2_verification"]
            para.step3_revision = result["step3_revision"]
            para.step4_finalization = result["step4_finalization"]
            para.translated_text = result["step4_finalization"]
            
            # 保存三美评分
            beauty_scores = result.get("beauty_scores", {})
            para.beauty_sound_score = beauty_scores.get("sound", 7.0)
            para.beauty_word_score = beauty_scores.get("word", 7.0)
            para.beauty_meaning_score = beauty_scores.get("meaning", 7.0)
            
            success_count += 1
            
            # 每5段提交一次，避免事务过大
            if (idx + 1) % 5 == 0:
                db.commit()
                
        except Exception as e:
            print(f"[Translate Chunk] Error at paragraph {para.paragraph_index}: {e}")
            continue
    
    db.commit()
    
    # 更新任务状态
    full_step1 = "\n\n".join([p.step1_translation or "" for p in paragraphs if p.step1_translation])
    full_step2 = "\n\n".join([p.step2_verification or "" for p in paragraphs if p.step2_verification])
    full_step3 = "\n\n".join([p.step3_revision or "" for p in paragraphs if p.step3_revision])
    full_step4 = "\n\n".join([p.step4_finalization or "" for p in paragraphs if p.step4_finalization])
    
    translation.step1_translation = full_step1
    translation.step2_verification = full_step2
    translation.step3_revision = full_step3
    translation.step4_finalization = full_step4
    translation.final_translation = full_step4
    translation.status = LiteraryTranslationStatus.COMPLETED
    translation.current_step = 4
    
    from datetime import datetime
    translation.completed_at = datetime.now()
    
    # 计算平均三美评分
    if paragraphs:
        translation.beauty_sound_score = sum([p.beauty_sound_score or 7.0 for p in paragraphs]) / len(paragraphs)
        translation.beauty_word_score = sum([p.beauty_word_score or 7.0 for p in paragraphs]) / len(paragraphs)
        translation.beauty_meaning_score = sum([p.beauty_meaning_score or 7.0 for p in paragraphs]) / len(paragraphs)
    
    db.commit()
    
    # 后台自动提取专业词汇
    background_tasks.add_task(auto_extract_terms_after_finalize, translation_id, db)
    
    return {
        "message": "一键翻译完成",
        "translation_id": translation_id,
        "total_paragraphs": total,
        "success_count": success_count,
        "beauty_scores": {
            "sound": translation.beauty_sound_score,
            "word": translation.beauty_word_score,
            "meaning": translation.beauty_meaning_score
        }
    }


@router.get("/translations/{translation_id}/progress")
async def get_translation_progress(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """
    获取长文本翻译进度
    """
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).all()
    
    total = len(paragraphs)
    completed = sum(1 for p in paragraphs if p.translated_text)
    
    return {
        "translation_id": translation_id,
        "status": translation.status,
        "total_paragraphs": total,
        "completed_paragraphs": completed,
        "progress_percentage": round((completed / total * 100), 1) if total > 0 else 0
    }
