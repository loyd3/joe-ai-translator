"""
文学翻译 API 路由
支持全文翻译、四步翻译流程、RAG参考、对照编辑
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
from app.database import get_db
from app.schemas.schemas import (
    LiteraryTranslationCreate, LiteraryTranslationResponse, 
    LiteraryTranslationListItem, LiteraryParagraphResponse,
    ParagraphUpdateRequest, LiteraryTranslationUpdate,
    ReferenceDocumentCreate, ReferenceDocumentResponse,
    ReferenceDocumentListItem, ReferenceDocumentUpdate,
    WorkflowStepResponse, LiteraryTranslationWorkflowResponse,
    ExportTranslationRequest
)
from app.models.models import (
    LiteraryTranslation, LiteraryParagraph, 
    ReferenceDocument, LiteraryTranslationStatus
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
# 四步翻译流程 API
# ============================================================

@router.post("/translations/{translation_id}/workflow/start")
async def start_translation_workflow(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """开始四步翻译流程"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    # 更新状态为翻译中
    translation.status = LiteraryTranslationStatus.TRANSLATING
    db.commit()
    
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    reference_content = get_reference_content(
        translation.reference_document_ids or [], db
    )
    
    # 执行第一步：翻译所有段落
    full_step1 = []
    for para in paragraphs:
        try:
            result = await client.literary_translate(
                para.source_text,
                translation.source_lang,
                translation.target_lang,
                translation.literary_type,
                reference_content
            )
            para.step1_translation = result
            para.translated_text = result
            full_step1.append(result)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Translation failed for paragraph {para.paragraph_index}: {str(e)}")
    
    translation.step1_translation = "\n\n".join(full_step1)
    translation.current_step = 2
    translation.status = LiteraryTranslationStatus.VERIFYING
    db.commit()
    
    return {"message": "Step 1 (Translation) completed", "current_step": 2}


@router.post("/translations/{translation_id}/workflow/verify")
async def verify_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """执行第二步：校验"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    if translation.current_step < 2:
        raise HTTPException(status_code=400, detail="Please complete step 1 first")
    
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    full_step2 = []
    total_sound_score = 0
    total_word_score = 0
    total_meaning_score = 0
    
    for para in paragraphs:
        try:
            result = await client.literary_verify(
                para.source_text,
                para.step1_translation or para.translated_text or "",
                translation.source_lang,
                translation.target_lang,
                translation.literary_type
            )
            verified = result.get("verified_translation", para.step1_translation)
            para.step2_verification = verified
            para.translated_text = verified
            
            para.beauty_sound_score = result.get("beauty_sound_score", 7.0)
            para.beauty_word_score = result.get("beauty_word_score", 7.0)
            para.beauty_meaning_score = result.get("beauty_meaning_score", 7.0)
            
            total_sound_score += para.beauty_sound_score
            total_word_score += para.beauty_word_score
            total_meaning_score += para.beauty_meaning_score
            
            full_step2.append(verified)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Verification failed for paragraph {para.paragraph_index}: {str(e)}")
    
    translation.step2_verification = "\n\n".join(full_step2)
    translation.current_step = 3
    translation.status = LiteraryTranslationStatus.REVISING
    
    # 计算平均分
    if paragraphs:
        translation.beauty_sound_score = total_sound_score / len(paragraphs)
        translation.beauty_word_score = total_word_score / len(paragraphs)
        translation.beauty_meaning_score = total_meaning_score / len(paragraphs)
    
    db.commit()
    
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
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    if translation.current_step < 3:
        raise HTTPException(status_code=400, detail="Please complete step 2 first")
    
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    full_step3 = []
    
    for para in paragraphs:
        try:
            # 构建校验分析结果
            verification_analysis = {
                "issues_found": [],
                "suggestions": [],
                "beauty_sound_score": para.beauty_sound_score,
                "beauty_word_score": para.beauty_word_score,
                "beauty_meaning_score": para.beauty_meaning_score,
            }
            
            result = await client.literary_revise(
                para.source_text,
                para.step2_verification or para.translated_text or "",
                verification_analysis,
                translation.source_lang,
                translation.target_lang,
                translation.literary_type
            )
            revised = result.get("revised_translation", para.step2_verification)
            para.step3_revision = revised
            para.translated_text = revised
            full_step3.append(revised)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Revision failed for paragraph {para.paragraph_index}: {str(e)}")
    
    translation.step3_revision = "\n\n".join(full_step3)
    translation.current_step = 4
    translation.status = LiteraryTranslationStatus.FINALIZING
    db.commit()
    
    return {"message": "Step 3 (Revision) completed", "current_step": 4}


@router.post("/translations/{translation_id}/workflow/finalize")
async def finalize_translation(
    translation_id: int,
    db: Session = Depends(get_db)
):
    """执行第四步：定稿"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    if translation.current_step < 4:
        raise HTTPException(status_code=400, detail="Please complete step 3 first")
    
    client = get_ai_client()
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    full_step4 = []
    
    for para in paragraphs:
        try:
            result = await client.literary_finalize(
                para.source_text,
                para.step3_revision or para.translated_text or "",
                translation.source_lang,
                translation.target_lang,
                translation.literary_type
            )
            finalized = result.get("final_translation", para.step3_revision)
            para.step4_finalization = finalized
            para.translated_text = finalized
            full_step4.append(finalized)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Finalization failed for paragraph {para.paragraph_index}: {str(e)}")
    
    translation.step4_finalization = "\n\n".join(full_step4)
    translation.final_translation = "\n\n".join(full_step4)
    translation.current_step = 4
    translation.status = LiteraryTranslationStatus.COMPLETED
    from datetime import datetime
    translation.completed_at = datetime.now()
    db.commit()
    
    return {"message": "Step 4 (Finalization) completed. Translation finished!", "current_step": 4}


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
# 导出功能
# ============================================================

@router.post("/translations/{translation_id}/export")
async def export_translation(
    translation_id: int,
    request: ExportTranslationRequest,
    db: Session = Depends(get_db)
):
    """导出翻译结果"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    # 构建导出内容
    lines = []
    
    if translation.title:
        lines.append(f"# {translation.title}")
        lines.append("")
    
    lines.append(f"原文语言: {translation.source_lang}")
    lines.append(f"译文语言: {translation.target_lang}")
    lines.append(f"文学类型: {translation.literary_type}")
    lines.append(f"生成时间: {translation.created_at}")
    lines.append("")
    
    if translation.beauty_sound_score:
        lines.append(f"音美评分: {translation.beauty_sound_score:.1f}/10")
    if translation.beauty_word_score:
        lines.append(f"词美评分: {translation.beauty_word_score:.1f}/10")
    if translation.beauty_meaning_score:
        lines.append(f"意美评分: {translation.beauty_meaning_score:.1f}/10")
    lines.append("")
    lines.append("=" * 50)
    lines.append("")
    
    for para in paragraphs:
        if request.include_source:
            lines.append("【原文】")
            lines.append(para.source_text)
            lines.append("")
            lines.append("【译文】")
        
        text = para.user_edited_text or para.translated_text or ""
        lines.append(text)
        lines.append("")
    
    content = "\n".join(lines)
    
    # 根据格式添加扩展名
    extension = request.format
    
    return {
        "filename": f"literary_translation_{translation_id}.{extension}",
        "content": content,
        "format": request.format
    }
