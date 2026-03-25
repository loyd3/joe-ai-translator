"""
翻译 API 路由
"""

import asyncio
import json
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langdetect import detect
from sqlalchemy.orm import Session

from app.core.ai_client import AIClient, get_ai_client
from app.core.auth import get_optional_user
from app.database import get_db
from app.models.models import BatchTranslation, TranslationHistory, User
from app.schemas.schemas import (
    BatchTranslationRequest,
    BatchTranslationResponse,
    LanguageInfo,
    TranslationHistoryItem,
    TranslationRequest,
    TranslationResponse,
)

router = APIRouter(prefix="/api/translate", tags=["translation"])

MAX_CHUNK_CHARS = 1800
LARGE_TEXT_THRESHOLD = 3200
MAX_CONCURRENCY = 4


def detect_language(text: str) -> str:
    """检测文本语言"""
    try:
        lang = detect(text)
        mapping = {
            "zh-cn": "zh",
            "zh-tw": "zh-TW",
            "zh-hk": "zh-TW",
        }
        return mapping.get(lang, lang)
    except Exception:
        return "en"


def _split_large_text(text: str, max_chunk_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """按段落/句号分块，减少超长请求报错。"""
    text = (text or "").strip()
    if not text:
        return [""]
    if len(text) <= max_chunk_chars:
        return [text]

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paras:
        paras = [p.strip() for p in text.split("\n") if p.strip()]
    if not paras:
        paras = [text]

    chunks: List[str] = []
    current = ""
    for para in paras:
        cand = f"{current}\n\n{para}" if current else para
        if len(cand) <= max_chunk_chars:
            current = cand
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(para) <= max_chunk_chars:
            current = para
            continue

        sentences = re.split(r"(?<=[。！？.!?])", para)
        part = ""
        for sen in sentences:
            if not sen:
                continue
            cand2 = f"{part}{sen}"
            if len(cand2) <= max_chunk_chars:
                part = cand2
            else:
                if part:
                    chunks.append(part)
                part = sen
                if len(part) > max_chunk_chars:
                    for i in range(0, len(part), max_chunk_chars):
                        chunks.append(part[i : i + max_chunk_chars])
                    part = ""
        if part:
            current = part

    if current:
        chunks.append(current)
    return chunks or [text]


async def _translate_chunk_with_retry(
    client: AIClient,
    text: str,
    source_lang: str,
    target_lang: str,
    context: Optional[str],
) -> str:
    """单块翻译，失败重试一次；仍失败则返回原文，保证整体不报错。"""
    try:
        return await client.translate(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            context=context,
        )
    except Exception:
        try:
            return await client.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                context=context,
                max_tokens=max(1024, client.effective_max_tokens // 2),
            )
        except Exception:
            return text


async def _translate_large_text(
    client: AIClient,
    text: str,
    source_lang: str,
    target_lang: str,
    context: Optional[str],
) -> str:
    """大文本并发翻译：按块并发，顺序合并，提升速度并降低失败率。"""
    chunks = _split_large_text(text)
    if len(chunks) == 1:
        return await _translate_chunk_with_retry(client, chunks[0], source_lang, target_lang, context)

    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def work(idx: int, chunk: str):
        async with sem:
            translated = await _translate_chunk_with_retry(client, chunk, source_lang, target_lang, context)
            return idx, translated

    results = await asyncio.gather(*[work(i, c) for i, c in enumerate(chunks)])
    results.sort(key=lambda x: x[0])
    return "\n\n".join([t for _, t in results])


@router.get("/languages", response_model=List[LanguageInfo])
async def get_languages(current_user: Optional[User] = Depends(get_optional_user)):
    """获取支持的语言列表"""
    return [LanguageInfo(code=code, name=name) for code, name in AIClient.SUPPORTED_LANGUAGES.items()]


@router.post("/", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """翻译文本（非流式）"""
    try:
        uid = current_user.id if current_user else None
        client = get_ai_client(uid)

        detected_lang = None
        source_lang = request.source_lang
        if source_lang == "auto":
            detected_lang = detect_language(request.text)
            source_lang = detected_lang

        if len(request.text or "") >= LARGE_TEXT_THRESHOLD:
            translated = await _translate_large_text(
                client=client,
                text=request.text,
                source_lang=source_lang,
                target_lang=request.target_lang,
                context=request.context,
            )
        else:
            translated = await _translate_chunk_with_retry(
                client=client,
                text=request.text,
                source_lang=source_lang,
                target_lang=request.target_lang,
                context=request.context,
            )

        history = TranslationHistory(
            user_id=uid,
            source_text=request.text,
            translated_text=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            ai_provider=client.settings.ai_provider,
            ai_model=client.model,
        )
        db.add(history)
        db.commit()

        return TranslationResponse(
            source_text=request.text,
            translated_text=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            detected_lang=detected_lang,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def translate_stream(
    request: TranslationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """翻译文本（流式）"""
    try:
        uid = current_user.id if current_user else None
        client = get_ai_client(uid)

        source_lang = request.source_lang
        if source_lang == "auto":
            source_lang = detect_language(request.text)

        translated_parts: List[str] = []

        async def generate():
            if len(request.text or "") >= LARGE_TEXT_THRESHOLD:
                chunks = _split_large_text(request.text)
                for c in chunks:
                    piece = await _translate_chunk_with_retry(
                        client=client,
                        text=c,
                        source_lang=source_lang,
                        target_lang=request.target_lang,
                        context=request.context,
                    )
                    translated_parts.append(piece)
                    yield f"data: {json.dumps({'chunk': piece})}\n\n"
            else:
                async for chunk in client.translate_stream(
                    text=request.text,
                    source_lang=source_lang,
                    target_lang=request.target_lang,
                    context=request.context,
                ):
                    translated_parts.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            full_text = "".join(translated_parts) if len(request.text or "") < LARGE_TEXT_THRESHOLD else "\n\n".join(translated_parts)
            history = TranslationHistory(
                user_id=uid,
                source_text=request.text,
                translated_text=full_text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                ai_provider=client.settings.ai_provider,
                ai_model=client.model,
            )
            db.add(history)
            db.commit()

            yield f"data: {json.dumps({'done': True})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[TranslationHistoryItem])
async def get_history(
    skip: int = 0,
    limit: int = 50,
    favorite_only: bool = False,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取翻译历史（匿名仅见 user_id 为空的记录）"""
    uid = current_user.id if current_user else None
    query = db.query(TranslationHistory).filter(TranslationHistory.user_id == uid)
    if favorite_only:
        query = query.filter(TranslationHistory.is_favorite == True)
    query = query.order_by(TranslationHistory.created_at.desc())
    history = query.offset(skip).limit(limit).all()
    return history


@router.post("/history/{history_id}/favorite")
async def toggle_favorite(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """切换收藏状态"""
    uid = current_user.id if current_user else None
    item = db.query(TranslationHistory).filter(
        TranslationHistory.id == history_id,
        TranslationHistory.user_id == uid,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Translation not found")

    item.is_favorite = not item.is_favorite
    db.commit()
    return {"id": history_id, "is_favorite": item.is_favorite}


@router.delete("/history/{history_id}")
async def delete_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """删除历史记录"""
    uid = current_user.id if current_user else None
    item = db.query(TranslationHistory).filter(
        TranslationHistory.id == history_id,
        TranslationHistory.user_id == uid,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Translation not found")

    db.delete(item)
    db.commit()
    return {"message": "Deleted successfully"}


@router.post("/batch", response_model=BatchTranslationResponse)
async def create_batch_translation(
    request: BatchTranslationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """创建批量翻译任务"""
    batch = BatchTranslation(
        user_id=current_user.id if current_user else None,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        items=[
            {"id": i, "source_text": text, "translated_text": None, "status": "pending"}
            for i, text in enumerate(request.items)
        ],
        total_items=len(request.items),
        status="pending",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    return batch


@router.get("/batch/{batch_id}", response_model=BatchTranslationResponse)
async def get_batch_translation(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """获取批量翻译任务状态"""
    uid = current_user.id if current_user else None
    batch = db.query(BatchTranslation).filter(
        BatchTranslation.id == batch_id,
        BatchTranslation.user_id == uid,
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch translation not found")
    return batch
