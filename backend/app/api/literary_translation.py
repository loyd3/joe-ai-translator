"""
文学翻译 API 路由
支持全文翻译、四步翻译流程、RAG参考、对照编辑
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from typing import List, Optional, AsyncGenerator
import json
import os
import io
import asyncio
import re
import tempfile
import shutil
import traceback
from app.database import get_db, SessionLocal
from app.core.auth import get_optional_user
from app.models.models import User
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


def _uid(user: Optional[User]) -> Optional[int]:
    """已登录返回用户 ID；匿名返回 None（共享数据与全局 AI 配置）"""
    return user.id if user else None


router = APIRouter(prefix="/api/literary", tags=["literary-translation"])

class WorkflowCancelled(Exception):
    pass

CANCELLED_TRANSLATIONS: set[int] = set()

# ============================================================
# 参考文档管理
# ============================================================

@router.post("/references", response_model=ReferenceDocumentResponse)
async def create_reference_document(
    request: ReferenceDocumentCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """创建参考文档（需 token）"""
    doc = ReferenceDocument(
        user_id=_uid(current_user),
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取参考文档列表（需 token）"""
    query = db.query(ReferenceDocument).filter(ReferenceDocument.user_id == _uid(current_user))
    if doc_type:
        query = query.filter(ReferenceDocument.doc_type == doc_type)
    if is_active is not None:
        query = query.filter(ReferenceDocument.is_active == is_active)
    query = query.order_by(ReferenceDocument.created_at.desc())
    return query.all()


@router.get("/references/{doc_id}", response_model=ReferenceDocumentResponse)
async def get_reference_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取参考文档详情（需 token）"""
    doc = db.query(ReferenceDocument).filter(
        ReferenceDocument.id == doc_id,
        ReferenceDocument.user_id == _uid(current_user),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Reference document not found")
    return doc


@router.put("/references/{doc_id}", response_model=ReferenceDocumentResponse)
async def update_reference_document(
    doc_id: int,
    request: ReferenceDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """更新参考文档（需 token）"""
    doc = db.query(ReferenceDocument).filter(
        ReferenceDocument.id == doc_id,
        ReferenceDocument.user_id == _uid(current_user),
    ).first()
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """删除参考文档（需 token）"""
    doc = db.query(ReferenceDocument).filter(
        ReferenceDocument.id == doc_id,
        ReferenceDocument.user_id == _uid(current_user),
    ).first()
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """上传参考文档文件（需 token）"""
    content = await file.read()
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else 'txt'
    if ext not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    try:
        text_content = parse_text_file(content, ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    doc = ReferenceDocument(
        user_id=_uid(current_user),
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

MAX_PARAGRAPH_SIZE = 2000


def _split_oversized_paragraph(text: str, max_size: int = MAX_PARAGRAPH_SIZE) -> List[str]:
    """将超长段落按句子边界拆分为不超过 max_size 的块"""
    if len(text) <= max_size:
        return [text]
    import re
    sentences = re.split(r'(?<=[。！？.!?\n])', text)
    chunks, current = [], ""
    for s in sentences:
        if not s:
            continue
        if len(current) + len(s) > max_size and current:
            chunks.append(current.strip())
            current = s
        else:
            current += s
    if current.strip():
        chunks.append(current.strip())
    if not chunks:
        chunks = [text[i:i+max_size] for i in range(0, len(text), max_size)]
    return chunks


def split_text_into_paragraphs(text: str, max_size: int = MAX_PARAGRAPH_SIZE) -> List[str]:
    """将文本分割成段落，并确保每段不超过 max_size 字符"""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    result = []
    for p in paragraphs:
        if len(p) > max_size:
            result.extend(_split_oversized_paragraph(p, max_size))
        else:
            result.append(p)
    return result


def _sanitize_text_for_api(text: str) -> str:
    """移除空字节和控制字符，避免 Windows 上触发 OSError [Errno 22] Invalid argument"""
    if not text:
        return text
    import re
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip() or text


def _safe_datetime_str(dt) -> str:
    """格式化 created_at 等时间，避免 Windows 上 strftime 触发 Errno 22"""
    if not dt:
        return ""
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except (OSError, ValueError):
        return dt.isoformat()[:16].replace("T", " ") if hasattr(dt, "isoformat") else str(dt)


def get_reference_content(doc_ids: List[int], db: Session, user_id: Optional[int] = None) -> str:
    """获取参考文档内容（可按 user_id 过滤）"""
    if not doc_ids:
        return ""
    query = db.query(ReferenceDocument).filter(
        ReferenceDocument.id.in_(doc_ids),
        ReferenceDocument.is_active == True,
    )
    if user_id is not None:
        query = query.filter(ReferenceDocument.user_id == user_id)
    docs = query.all()
    
    contents = []
    for doc in docs:
        contents.append(f"=== {doc.name} ({doc.doc_type}) ===\n{doc.content}\n")
    
    return "\n".join(contents)


def get_reference_and_requirements(translation: LiteraryTranslation, db: Session) -> str:
    """参考文档 + 用户翻译需求，供 AI 提示使用"""
    ref = get_reference_content(translation.reference_document_ids or [], db, translation.user_id)
    if translation.user_requirements and translation.user_requirements.strip():
        req = f"\n\n## 用户翻译需求\n{translation.user_requirements.strip()}"
        ref = (ref + req) if ref else req.lstrip()
    return ref or ""


@router.post("/translations", response_model=LiteraryTranslationResponse)
async def create_literary_translation(
    request: LiteraryTranslationCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """创建文学翻译任务（需 token）"""
    translation = LiteraryTranslation(
        user_id=_uid(current_user),
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
    
    paragraphs = split_text_into_paragraphs(request.source_text)
    
    for idx, para_text in enumerate(paragraphs):
        paragraph = LiteraryParagraph(
            translation_id=translation.id,
            paragraph_index=idx,
            source_text=para_text
        )
        db.add(paragraph)
    
    db.commit()
    db.refresh(translation)
    return translation


@router.get("/translations", response_model=List[LiteraryTranslationListItem])
async def list_literary_translations(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取文学翻译任务列表（需 token）"""
    try:
        query = db.query(LiteraryTranslation).filter(LiteraryTranslation.user_id == _uid(current_user))
        if status:
            query = query.filter(LiteraryTranslation.status == status)
        query = query.order_by(LiteraryTranslation.created_at.desc())
        return query.offset(skip).limit(limit).all()
    except OperationalError as e:
        err_msg = str(getattr(e, "orig", e))
        if "Unknown column" in err_msg:
            hint = "Database schema is outdated. Run migration: mysql -u root -p aitranslator < backend/migrations/schema_update_literary_translations.sql"
            if "user_id" in err_msg:
                hint = "Missing user_id column. Run: mysql -u root -p aitranslator < backend/migrations/add_user_id_to_literary.sql"
            raise HTTPException(status_code=503, detail=hint)
        raise


# 批量路由必须在 /{translation_id} 之前定义
async def _run_batch_workflow_background(translation_ids: list, user_id: int):
    """依次执行多个任务的翻译流程，前一个完成后才开始下一个"""
    for tid in translation_ids:
        db = SessionLocal()
        try:
            translation = db.query(LiteraryTranslation).filter(
                LiteraryTranslation.id == tid,
                LiteraryTranslation.user_id == user_id,
            ).first()
            if not translation:
                continue
            translation.current_step = 1
            translation.status = LiteraryTranslationStatus.TRANSLATING
            translation.step1_translation = None
            translation.step2_verification = None
            translation.step3_revision = None
            translation.step4_finalization = None
            translation.final_translation = None
            translation.beauty_sound_score = None
            translation.beauty_word_score = None
            translation.beauty_meaning_score = None
            translation.completed_at = None
            db.commit()
        except Exception:
            db.close()
            continue
        finally:
            db.close()

        try:
            await _run_workflow_background(tid, user_id)
        except Exception as e:
            print(f"[BatchWorkflow] Translation {tid} failed: {e}")


@router.post("/translations/batch/workflow/start")
async def start_batch_workflow(
    request: dict,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """批量启动翻译流程（需 token）"""
    translation_ids = request.get("translation_ids", [])
    if not translation_ids:
        raise HTTPException(status_code=400, detail="请选择至少一个任务")

    running_statuses = {
        LiteraryTranslationStatus.TRANSLATING,
        LiteraryTranslationStatus.VERIFYING,
        LiteraryTranslationStatus.REVISING,
        LiteraryTranslationStatus.FINALIZING,
    }

    valid_ids = []
    for tid in translation_ids:
        t = db.query(LiteraryTranslation).filter(
            LiteraryTranslation.id == tid,
            LiteraryTranslation.user_id == _uid(current_user),
        ).first()
        if not t:
            continue
        if t.status in running_statuses:
            continue
        t.status = LiteraryTranslationStatus.PENDING
        valid_ids.append(tid)

    if not valid_ids:
        raise HTTPException(status_code=400, detail="没有可启动的任务")

    db.commit()
    asyncio.create_task(_run_batch_workflow_background(valid_ids, _uid(current_user)))

    return {"message": f"已加入队列 {len(valid_ids)} 个任务", "translation_ids": valid_ids}


@router.get("/translations/{translation_id}", response_model=LiteraryTranslationResponse)
async def get_literary_translation(
    translation_id: int,
    include_paragraphs: bool = True,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取文学翻译任务详情（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    return translation


@router.put("/translations/{translation_id}", response_model=LiteraryTranslationResponse)
async def update_literary_translation(
    translation_id: int,
    request: LiteraryTranslationUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """更新文学翻译任务（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    if request.title is not None:
        translation.title = request.title
    if request.source_text is not None:
        translation.source_text = request.source_text
    if request.final_translation is not None:
        translation.final_translation = request.final_translation
    if request.status is not None:
        allowed = ("pending", "translating", "verifying", "revising", "finalizing", "completed", "failed")
        if request.status not in allowed:
            raise HTTPException(status_code=400, detail=f"status must be one of: {allowed}")
        translation.status = request.status

    db.commit()
    db.refresh(translation)
    return translation


@router.delete("/translations/{translation_id}")
async def delete_literary_translation(
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """删除文学翻译任务（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    db.delete(translation)
    db.commit()
    return {"message": "Translation deleted successfully"}


# ============================================================
# 四步翻译流程 API（内部执行函数供 run_all 复用）
# ============================================================

async def _execute_step1(translation_id: int, db: Session, user_id: int) -> None:
    """执行第一步：初译（逐段翻译，每段完成即保存）"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    translation.status = LiteraryTranslationStatus.TRANSLATING
    db.commit()
    client = get_ai_client(user_id)
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    reference_content = get_reference_and_requirements(translation, db)
    full_step1 = []
    for para in paragraphs:
        if translation_id in CANCELLED_TRANSLATIONS:
            translation.status = LiteraryTranslationStatus.FAILED
            translation.error_message = "Cancelled by user"
            db.commit()
            raise WorkflowCancelled()
        source_text = _sanitize_text_for_api(para.source_text or "")
        ref_safe = _sanitize_text_for_api(reference_content) if reference_content else ""
        result = await client.literary_translate(
            source_text, translation.source_lang, translation.target_lang,
            translation.literary_type, ref_safe
        )
        para.step1_translation = result
        para.translated_text = result
        full_step1.append(result)
        db.commit()
    translation.step1_translation = "\n\n".join(full_step1)
    translation.current_step = 2
    translation.status = LiteraryTranslationStatus.VERIFYING
    db.commit()


async def _execute_step2(translation_id: int, db: Session, user_id: int) -> None:
    """执行第二步：校验"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation or translation.current_step < 2:
        raise HTTPException(status_code=400, detail="Please complete step 1 first")
    client = get_ai_client(user_id)
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    full_step2 = []
    total_sound, total_word, total_meaning = 0, 0, 0
    for para in paragraphs:
        if translation_id in CANCELLED_TRANSLATIONS:
            translation.status = LiteraryTranslationStatus.FAILED
            translation.error_message = "Cancelled by user"
            db.commit()
            raise WorkflowCancelled()
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
        db.commit()
    translation.step2_verification = "\n\n".join(full_step2)
    translation.current_step = 3
    translation.status = LiteraryTranslationStatus.REVISING
    if paragraphs:
        translation.beauty_sound_score = total_sound / len(paragraphs)
        translation.beauty_word_score = total_word / len(paragraphs)
        translation.beauty_meaning_score = total_meaning / len(paragraphs)
    db.commit()


async def _execute_step3(translation_id: int, db: Session, user_id: int) -> None:
    """执行第三步：修改"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation or translation.current_step < 3:
        raise HTTPException(status_code=400, detail="Please complete step 2 first")
    client = get_ai_client(user_id)
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    full_step3 = []
    for para in paragraphs:
        if translation_id in CANCELLED_TRANSLATIONS:
            translation.status = LiteraryTranslationStatus.FAILED
            translation.error_message = "Cancelled by user"
            db.commit()
            raise WorkflowCancelled()
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
        db.commit()
    translation.step3_revision = "\n\n".join(full_step3)
    translation.current_step = 4
    translation.status = LiteraryTranslationStatus.FINALIZING
    db.commit()


STEP4_BATCH_CHARS = 6000


async def _execute_step4(translation_id: int, db: Session, user_id: int) -> None:
    """执行第四步：定稿 — 分批整合段落统一处理，支持大文件"""
    translation = db.query(LiteraryTranslation).filter(LiteraryTranslation.id == translation_id).first()
    if not translation or translation.current_step < 4:
        raise HTTPException(status_code=400, detail="Please complete step 3 first")
    client = get_ai_client(user_id)
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()

    PARA_SEP = "\n\n"
    total_chars = sum(len(p.step3_revision or p.translated_text or "") for p in paragraphs)

    if total_chars <= STEP4_BATCH_CHARS:
        if translation_id in CANCELLED_TRANSLATIONS:
            translation.status = LiteraryTranslationStatus.FAILED
            translation.error_message = "Cancelled by user"
            db.commit()
            raise WorkflowCancelled()
        full_source = PARA_SEP.join(p.source_text for p in paragraphs)
        full_revised = PARA_SEP.join(
            (p.step3_revision or p.translated_text or "") for p in paragraphs
        )
        result = await client.literary_finalize(
            full_source, full_revised,
            translation.source_lang, translation.target_lang, translation.literary_type
        )
        finalized_full = result.get("final_translation", full_revised)
        finalized_parts = finalized_full.split(PARA_SEP)
        for i, para in enumerate(paragraphs):
            text = finalized_parts[i].strip() if i < len(finalized_parts) else (para.step3_revision or para.translated_text or "")
            para.step4_finalization = text
            para.translated_text = text
        if len(finalized_parts) > len(paragraphs):
            extra = PARA_SEP.join(finalized_parts[len(paragraphs):])
            paragraphs[-1].step4_finalization += PARA_SEP + extra
            paragraphs[-1].translated_text = paragraphs[-1].step4_finalization
    else:
        batches: list[list] = []
        current_batch: list = []
        current_size = 0
        for para in paragraphs:
            p_size = len(para.step3_revision or para.translated_text or "")
            if current_size + p_size > STEP4_BATCH_CHARS and current_batch:
                batches.append(current_batch)
                current_batch = [para]
                current_size = p_size
            else:
                current_batch.append(para)
                current_size += p_size
        if current_batch:
            batches.append(current_batch)

        for batch in batches:
            if translation_id in CANCELLED_TRANSLATIONS:
                translation.status = LiteraryTranslationStatus.FAILED
                translation.error_message = "Cancelled by user"
                db.commit()
                raise WorkflowCancelled()
            batch_source = PARA_SEP.join(p.source_text for p in batch)
            batch_revised = PARA_SEP.join(
                (p.step3_revision or p.translated_text or "") for p in batch
            )
            result = await client.literary_finalize(
                batch_source, batch_revised,
                translation.source_lang, translation.target_lang, translation.literary_type
            )
            finalized_text = result.get("final_translation", batch_revised)
            finalized_parts = finalized_text.split(PARA_SEP)
            for i, para in enumerate(batch):
                text = finalized_parts[i].strip() if i < len(finalized_parts) else (para.step3_revision or para.translated_text or "")
                para.step4_finalization = text
                para.translated_text = text
            if len(finalized_parts) > len(batch):
                extra = PARA_SEP.join(finalized_parts[len(batch):])
                batch[-1].step4_finalization += PARA_SEP + extra
                batch[-1].translated_text = batch[-1].step4_finalization

    finalized_all = PARA_SEP.join(
        (p.step4_finalization or p.translated_text or "") for p in paragraphs
    )
    translation.step4_finalization = finalized_all
    translation.final_translation = finalized_all
    translation.current_step = 4
    translation.status = LiteraryTranslationStatus.COMPLETED
    from datetime import datetime
    translation.completed_at = datetime.now()
    db.commit()
    try:
        await auto_extract_terms_after_finalize(translation_id, db, user_id)
    except Exception as e:
        print(f"[Auto Extract Terms] Error: {e}")


def _format_error_debug(exc: BaseException, step: int, step_name: str) -> str:
    """将异常格式化为带调试信息的 error_message（便于排查 [Errno 22] 等）"""
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_str = "".join(tb_lines).strip()
    # 限制长度，避免 DB 字段过长；保留最后约 2500 字符（通常含关键堆栈）
    max_tb = 2500
    if len(tb_str) > max_tb:
        tb_str = "...\n" + tb_str[-max_tb:]
    return (
        f"[Step {step} - {step_name}] {type(exc).__name__}: {exc}\n\n"
        f"Traceback:\n{tb_str}"
    )


async def _run_workflow_background(translation_id: int, user_id: int):
    """后台依次执行四步翻译流程：初译 → 校验 → 修改 → 定稿"""
    db = SessionLocal()
    steps = [
        (1, "初译", _execute_step1),
        (2, "校验", _execute_step2),
        (3, "修改", _execute_step3),
        (4, "定稿", _execute_step4),
    ]
    try:
        for step_num, step_name, step_fn in steps:
            await step_fn(translation_id, db, user_id)
    except WorkflowCancelled:
        try:
            translation = db.query(LiteraryTranslation).filter(
                LiteraryTranslation.id == translation_id
            ).first()
            if translation:
                translation.status = LiteraryTranslationStatus.FAILED
                if not translation.error_message:
                    translation.error_message = "Cancelled by user"
                db.commit()
        except Exception:
            pass
    except Exception as e:
        # 确定失败步骤（当前步骤尚未完成）
        failed_step = 1
        failed_name = "初译"
        try:
            t = db.query(LiteraryTranslation).filter(
                LiteraryTranslation.id == translation_id
            ).first()
            if t is not None:
                # current_step 是“正在做”的步骤，失败时就是该步
                failed_step = getattr(t, "current_step", 1) or 1
                for sn, sname, _ in steps:
                    if sn == failed_step:
                        failed_name = sname
                        break
        except Exception:
            pass
        try:
            translation = db.query(LiteraryTranslation).filter(
                LiteraryTranslation.id == translation_id
            ).first()
            if translation:
                translation.status = LiteraryTranslationStatus.FAILED
                translation.error_message = _format_error_debug(e, failed_step, failed_name)
                db.commit()
        except Exception:
            pass
        traceback.print_exc()
        print(f"[Workflow] Translation {translation_id} failed: {e}")
    finally:
        db.close()


@router.post("/translations/{translation_id}/workflow/start")
async def start_translation_workflow(
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """启动四步翻译流程（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    running_statuses = {
        LiteraryTranslationStatus.TRANSLATING,
        LiteraryTranslationStatus.VERIFYING,
        LiteraryTranslationStatus.REVISING,
        LiteraryTranslationStatus.FINALIZING,
    }
    if translation.status in running_statuses:
        raise HTTPException(status_code=409, detail="翻译流程正在执行中")

    translation.current_step = 1
    translation.status = LiteraryTranslationStatus.TRANSLATING
    translation.step1_translation = None
    translation.step2_verification = None
    translation.step3_revision = None
    translation.step4_finalization = None
    translation.final_translation = None
    translation.beauty_sound_score = None
    translation.beauty_word_score = None
    translation.beauty_meaning_score = None
    translation.completed_at = None
    translation.error_message = None  # 新流程开始时清空旧错误
    db.commit()

    asyncio.create_task(_run_workflow_background(translation_id, _uid(current_user)))

    return {"message": "翻译流程已启动", "status": "translating"}

@router.post("/translations/{translation_id}/workflow/stop")
async def stop_translation_workflow(
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    running_statuses = {
        LiteraryTranslationStatus.TRANSLATING,
        LiteraryTranslationStatus.VERIFYING,
        LiteraryTranslationStatus.REVISING,
        LiteraryTranslationStatus.FINALIZING,
    }
    if translation.status not in running_statuses:
        return {"message": "当前未在运行", "status": translation.status}
    CANCELLED_TRANSLATIONS.add(translation_id)
    translation.status = LiteraryTranslationStatus.FAILED
    translation.error_message = "Cancelled by user"
    db.commit()
    return {"message": "已终止", "status": "failed"}


@router.get("/translations/{translation_id}/workflow", response_model=LiteraryTranslationWorkflowResponse)
async def get_workflow_status(
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取工作流状态（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()

    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    status_to_running_step = {
        "translating": 1, "verifying": 2, "revising": 3, "finalizing": 4,
    }
    running_step = status_to_running_step.get(translation.status, 0)

    step_fields = [
        (1, "翻译", translation.step1_translation),
        (2, "校验", translation.step2_verification),
        (3, "修改", translation.step3_revision),
        (4, "定稿", translation.step4_finalization),
    ]

    steps = []
    for step_num, step_name, result in step_fields:
        if result:
            step_status = "completed"
        elif step_num == running_step:
            step_status = "processing"
        else:
            step_status = "pending"
        truncated = result[:200] + "..." if result and len(result) > 200 else result
        steps.append(WorkflowStepResponse(
            step=step_num, step_name=step_name, status=step_status, result=truncated,
        ))

    para_total = 0
    para_done = 0
    if running_step > 0:
        all_paras = db.query(LiteraryParagraph).filter(
            LiteraryParagraph.translation_id == translation_id
        ).all()
        para_total = len(all_paras)
        step_field_map = {1: "step1_translation", 2: "step2_verification", 3: "step3_revision", 4: "step4_finalization"}
        field = step_field_map.get(running_step)
        if field:
            para_done = sum(1 for p in all_paras if getattr(p, field, None))

    return LiteraryTranslationWorkflowResponse(
        translation_id=translation_id,
        current_step=translation.current_step,
        overall_status=translation.status,
        steps=steps,
        paragraph_total=para_total,
        paragraph_done=para_done,
    )


# ============================================================
# 段落管理
# ============================================================

@router.get("/translations/{translation_id}/paragraphs", response_model=List[LiteraryParagraphResponse])
async def get_paragraphs(
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取所有段落（需 token）"""
    t = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Translation not found")
    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation_id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    
    return paragraphs


@router.put("/paragraphs/{paragraph_id}", response_model=LiteraryParagraphResponse)
async def update_paragraph(
    paragraph_id: int,
    request: ParagraphUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """更新段落译文（需 token）"""
    paragraph = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.id == paragraph_id
    ).first()
    
    if not paragraph:
        raise HTTPException(status_code=404, detail="Paragraph not found")
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == paragraph.translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    
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
    lines.append(f"生成时间: {_safe_datetime_str(translation.created_at)}")
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
    lines.append(f"- **生成时间**: {_safe_datetime_str(translation.created_at)}")
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
    html_parts.append(f"<p><strong>生成时间：</strong>{_safe_datetime_str(translation.created_at)}</p>")
    
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
    writer.writerow(["生成时间", _safe_datetime_str(translation.created_at)])
    
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


def _safe_export_basename(name: Optional[str]) -> str:
    """生成安全文件名：<原文名>译文，过滤非法字符并限制长度。"""
    base = (name or "").strip() or "翻译结果"
    # Windows/macOS 常见非法字符
    base = re.sub(r'[\\\\/:*?"<>|]+', "_", base)
    base = re.sub(r"\s+", " ", base).strip().strip(".")
    if not base:
        base = "翻译结果"
    # 给扩展名预留空间，避免超长
    if len(base) > 80:
        base = base[:80].rstrip()
    return f"{base}译文"


@router.post("/translations/{translation_id}/export")
async def export_translation(
    translation_id: int,
    request: ExportTranslationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """导出翻译结果（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
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
        "filename": f"{_safe_export_basename(translation.title)}.{format_ext}",
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取专业词汇列表（需 token）"""
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """创建专业词汇（需 token）"""
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """更新专业词汇（需 token）"""
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """删除专业词汇（需 token）"""
    term = db.query(ProfessionalTerm).filter(ProfessionalTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    db.delete(term)
    db.commit()
    return {"message": "Term deleted successfully"}


@router.get("/terms/categories")
async def get_term_categories(
    literary_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取词汇分类列表（需 token）"""
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取翻译任务的专业词汇总结（需 token）"""
    t = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Translation not found")
    summary = db.query(TranslationTermSummary).filter(
        TranslationTermSummary.translation_id == translation_id
    ).first()

    if not summary:
        raise HTTPException(status_code=404, detail="Term summary not found")

    return summary


@router.post("/translations/{translation_id}/terms/extract")
async def extract_terms_from_translation(
    translation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """从翻译任务中提取专业词汇（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
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
    client = get_ai_client(_uid(current_user))
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
    db: Session,
    user_id: int,
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
        client = get_ai_client(user_id)
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

# 支持的上传格式：txt、docx、pdf、mobi 及常见文本格式
SUPPORTED_UPLOAD_EXTENSIONS = {
    'txt', 'md', 'markdown', 'text',
    'docx', 'doc',   # Word
    'pdf',
    'mobi', 'azw',   # 电子书
    'html', 'htm', 'xhtml', 'xml', 'json', 'csv',
    'log', 'rst', 'tex', 'srt', 'sub', 'vtt', 'yaml', 'yml', 'ini', 'cfg', 'properties',
}


def _decode_text_content(content: bytes) -> str:
    """多种编码尝试解码"""
    for encoding in ('utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1'):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode('utf-8', errors='ignore')


def _extract_text_docx(content: bytes) -> str:
    """从 Word docx 提取正文"""
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_text_pdf(content: bytes) -> str:
    """从 PDF 提取正文"""
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts)


def _extract_text_mobi(content: bytes) -> str:
    """从 MOBI/AZW 电子书提取正文。解压后可能是 HTML/EPUB/PDF，按类型处理"""
    import mobi
    fd, path = tempfile.mkstemp(suffix=".mobi")
    try:
        os.write(fd, content)
        os.close(fd)
        tempdir, filepath = mobi.extract(path)
        try:
            ext = filepath.split(".")[-1].lower() if "." in filepath else ""
            if ext == "pdf":
                with open(filepath, "rb") as f:
                    return _extract_text_pdf(f.read())
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()
            text = re.sub(r"<[^>]+>", " ", raw)
            text = re.sub(r"\s+", " ", text).strip()
            return text
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def parse_text_file(content: bytes, file_type: str) -> str:
    """根据扩展名解析文件内容为纯文本。支持 txt、docx、pdf、mobi 等"""
    ext = (file_type or "").lower()
    try:
        if ext in ("docx", "doc"):
            return _extract_text_docx(content)
        if ext == "pdf":
            return _extract_text_pdf(content)
        if ext in ("mobi", "azw"):
            return _extract_text_mobi(content)
        # 文本类：多编码解码
        text = _decode_text_content(content)
        return text
    except Exception as e:
        raise ValueError(f"无法解析文件 ({ext}): {str(e)}")


def split_long_text(text: str, max_chunk_size: int = MAX_PARAGRAPH_SIZE) -> List[str]:
    """
    将长文本分段，每段不超过 max_chunk_size 字符
    尽量在段落边界处分割；单段超长时按句子边界拆
    """
    return split_text_into_paragraphs(text, max_chunk_size)


MAX_UPLOAD_SIZE = 20 * 1024 * 1024


@router.post("/parse-file")
async def parse_uploaded_file(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """解析上传文件并返回提取的正文（需 token）"""
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}")
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大（{len(content) / 1024 / 1024:.1f}MB），最大支持 {MAX_UPLOAD_SIZE // 1024 // 1024}MB"
        )
    try:
        text = parse_text_file(content, ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    para_count = len(split_text_into_paragraphs(text))
    return {"text": text, "filename": file.filename, "char_count": len(text), "paragraph_count": para_count}


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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """上传文件并创建翻译任务（需 token）"""
    file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        supported = ', '.join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_extension}. 支持: {supported}"
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
        user_id=_uid(current_user),
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
            await _execute_step1(translation.id, db, _uid(current_user))
            await _execute_step2(translation.id, db, _uid(current_user))
            await _execute_step3(translation.id, db, _uid(current_user))
            await _execute_step4(translation.id, db, _uid(current_user))
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """一键翻译所有段落（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
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
    
    client = get_ai_client(_uid(current_user))
    
    # 获取参考文档内容
    reference_content = ""
    if translation.reference_document_ids:
        docs = db.query(ReferenceDocument).filter(
            ReferenceDocument.id.in_(translation.reference_document_ids),
            ReferenceDocument.is_active == True,
            ReferenceDocument.user_id == _uid(current_user),
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
    background_tasks.add_task(auto_extract_terms_after_finalize, translation_id, db, _uid(current_user))
    
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取长文本翻译进度（需 token）"""
    translation = db.query(LiteraryTranslation).filter(
        LiteraryTranslation.id == translation_id,
        LiteraryTranslation.user_id == _uid(current_user),
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
