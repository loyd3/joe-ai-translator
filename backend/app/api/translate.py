"""
翻译 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.schemas import (
    TranslationRequest, TranslationResponse, TranslationHistoryItem,
    BatchTranslationRequest, BatchTranslationResponse, LanguageInfo
)
from app.models.models import TranslationHistory, BatchTranslation
from app.core.ai_client import get_ai_client, AIClient
from langdetect import detect
import json

router = APIRouter(prefix="/api/translate", tags=["translation"])


def detect_language(text: str) -> str:
    """检测文本语言"""
    try:
        lang = detect(text)
        # 将 langdetect 代码映射到我们的代码
        mapping = {
            "zh-cn": "zh",
            "zh-tw": "zh-TW",
            "zh-hk": "zh-TW",
        }
        return mapping.get(lang, lang)
    except:
        return "en"


@router.get("/languages", response_model=List[LanguageInfo])
async def get_languages():
    """获取支持的语言列表"""
    client = AIClient()
    return [
        LanguageInfo(code=code, name=name)
        for code, name in client.SUPPORTED_LANGUAGES.items()
    ]


@router.post("/", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    db: Session = Depends(get_db)
):
    """翻译文本（非流式）"""
    try:
        client = get_ai_client()
        
        # 检测源语言
        detected_lang = None
        source_lang = request.source_lang
        if source_lang == "auto":
            detected_lang = detect_language(request.text)
            source_lang = detected_lang
        
        # 执行翻译
        translated = await client.translate(
            text=request.text,
            source_lang=source_lang,
            target_lang=request.target_lang,
            context=request.context
        )
        
        # 保存到历史记录
        history = TranslationHistory(
            source_text=request.text,
            translated_text=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            ai_provider=client.settings.ai_provider,
            ai_model=client.model
        )
        db.add(history)
        db.commit()
        
        return TranslationResponse(
            source_text=request.text,
            translated_text=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            detected_lang=detected_lang
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def translate_stream(
    request: TranslationRequest,
    db: Session = Depends(get_db)
):
    """翻译文本（流式）"""
    try:
        client = get_ai_client()
        
        # 检测源语言
        source_lang = request.source_lang
        if source_lang == "auto":
            source_lang = detect_language(request.text)
        
        translated_parts = []
        
        async def generate():
            async for chunk in client.translate_stream(
                text=request.text,
                source_lang=source_lang,
                target_lang=request.target_lang,
                context=request.context
            ):
                translated_parts.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # 保存完整翻译到历史
            full_text = "".join(translated_parts)
            history = TranslationHistory(
                source_text=request.text,
                translated_text=full_text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                ai_provider=client.settings.ai_provider,
                ai_model=client.model
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
    db: Session = Depends(get_db)
):
    """获取翻译历史"""
    query = db.query(TranslationHistory)
    if favorite_only:
        query = query.filter(TranslationHistory.is_favorite == True)
    query = query.order_by(TranslationHistory.created_at.desc())
    history = query.offset(skip).limit(limit).all()
    return history


@router.post("/history/{history_id}/favorite")
async def toggle_favorite(
    history_id: int,
    db: Session = Depends(get_db)
):
    """切换收藏状态"""
    item = db.query(TranslationHistory).filter(TranslationHistory.id == history_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    item.is_favorite = not item.is_favorite
    db.commit()
    return {"id": history_id, "is_favorite": item.is_favorite}


@router.delete("/history/{history_id}")
async def delete_history(
    history_id: int,
    db: Session = Depends(get_db)
):
    """删除历史记录"""
    item = db.query(TranslationHistory).filter(TranslationHistory.id == history_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Translation not found")
    
    db.delete(item)
    db.commit()
    return {"message": "Deleted successfully"}


@router.post("/batch", response_model=BatchTranslationResponse)
async def create_batch_translation(
    request: BatchTranslationRequest,
    db: Session = Depends(get_db)
):
    """创建批量翻译任务"""
    batch = BatchTranslation(
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        items=[
            {"id": i, "source_text": text, "translated_text": None, "status": "pending"}
            for i, text in enumerate(request.items)
        ],
        total_items=len(request.items),
        status="pending"
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    
    return batch


@router.get("/batch/{batch_id}", response_model=BatchTranslationResponse)
async def get_batch_translation(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """获取批量翻译任务状态"""
    batch = db.query(BatchTranslation).filter(BatchTranslation.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch translation not found")
    return batch
