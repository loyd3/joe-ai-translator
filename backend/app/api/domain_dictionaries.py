"""
外部专业词典 API：CRUD + CSV/XLSX 导入
"""

from __future__ import annotations

import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import DomainDictionary, DomainDictionaryTerm
from app.schemas.schemas import (
    DomainDictionaryCreate,
    DomainDictionaryResponse,
    DomainDictionaryTermCreate,
    DomainDictionaryTermResponse,
    DomainDictionaryTermUpdate,
    DomainDictionaryUpdate,
)
from app.services.term_hit_service import resolve_default_dictionary_ids

router = APIRouter(prefix="/api/domain-dictionaries", tags=["domain-dictionaries"])


def _refresh_term_count(db: Session, dictionary_id: int) -> None:
    count = (
        db.query(DomainDictionaryTerm)
        .filter(DomainDictionaryTerm.dictionary_id == dictionary_id)
        .count()
    )
    row = db.query(DomainDictionary).filter(DomainDictionary.id == dictionary_id).first()
    if row:
        row.term_count = count


def _normalize_aliases(raw) -> Optional[List[str]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        vals = [str(x).strip() for x in raw if str(x).strip()]
        return vals or None
    text = str(raw).strip()
    if not text:
        return None
    if ";" in text:
        parts = text.split(";")
    elif "|" in text:
        parts = text.split("|")
    else:
        parts = text.split(",")
    vals = [p.strip() for p in parts if p.strip()]
    return vals or None


@router.get("", response_model=List[DomainDictionaryResponse])
async def list_dictionaries(
    literary_type: Optional[str] = None,
    source_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    is_active: Optional[bool] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(DomainDictionary)
    if literary_type:
        q = q.filter(
            (DomainDictionary.literary_type == literary_type)
            | (DomainDictionary.literary_type.is_(None))
            | (DomainDictionary.literary_type == "")
            | (DomainDictionary.literary_type == "general")
        )
    if source_lang:
        q = q.filter(DomainDictionary.source_lang == source_lang)
    if target_lang:
        q = q.filter(DomainDictionary.target_lang == target_lang)
    if is_active is not None:
        q = q.filter(DomainDictionary.is_active.is_(bool(is_active)))
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(
            (DomainDictionary.name.like(like)) | (DomainDictionary.description.like(like))
        )
    return q.order_by(DomainDictionary.id.desc()).all()


@router.get("/defaults")
async def list_default_dictionary_ids(
    literary_type: str = Query(...),
    source_lang: str = Query(...),
    target_lang: str = Query(...),
    db: Session = Depends(get_db),
):
    ids = resolve_default_dictionary_ids(
        db,
        literary_type=literary_type,
        source_lang=source_lang,
        target_lang=target_lang,
    )
    return {"ids": ids}


@router.post("", response_model=DomainDictionaryResponse)
async def create_dictionary(request: DomainDictionaryCreate, db: Session = Depends(get_db)):
    row = DomainDictionary(
        name=request.name.strip(),
        description=request.description,
        literary_type=(request.literary_type or "").strip() or None,
        source_lang=request.source_lang.strip(),
        target_lang=request.target_lang.strip(),
        source="manual",
        is_active=request.is_active,
        is_default_for_domain=request.is_default_for_domain,
        term_count=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/{dictionary_id}", response_model=DomainDictionaryResponse)
async def get_dictionary(dictionary_id: int, db: Session = Depends(get_db)):
    row = db.query(DomainDictionary).filter(DomainDictionary.id == dictionary_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="词典不存在")
    return row


@router.put("/{dictionary_id}", response_model=DomainDictionaryResponse)
async def update_dictionary(
    dictionary_id: int,
    request: DomainDictionaryUpdate,
    db: Session = Depends(get_db),
):
    row = db.query(DomainDictionary).filter(DomainDictionary.id == dictionary_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="词典不存在")
    fields = getattr(request, "model_fields_set", None) or set()
    if "name" in fields and request.name is not None:
        row.name = request.name.strip()
    if "description" in fields:
        row.description = request.description
    if "literary_type" in fields:
        row.literary_type = (request.literary_type or "").strip() or None
    if "source_lang" in fields and request.source_lang:
        row.source_lang = request.source_lang.strip()
    if "target_lang" in fields and request.target_lang:
        row.target_lang = request.target_lang.strip()
    if "is_default_for_domain" in fields and request.is_default_for_domain is not None:
        row.is_default_for_domain = request.is_default_for_domain
    if "is_active" in fields and request.is_active is not None:
        row.is_active = request.is_active
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{dictionary_id}")
async def delete_dictionary(dictionary_id: int, db: Session = Depends(get_db)):
    row = db.query(DomainDictionary).filter(DomainDictionary.id == dictionary_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="词典不存在")
    db.delete(row)
    db.commit()
    return {"message": "已删除"}


@router.get("/{dictionary_id}/terms", response_model=List[DomainDictionaryTermResponse])
async def list_terms(
    dictionary_id: int,
    keyword: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    exists = db.query(DomainDictionary.id).filter(DomainDictionary.id == dictionary_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="词典不存在")
    q = db.query(DomainDictionaryTerm).filter(DomainDictionaryTerm.dictionary_id == dictionary_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(
            (DomainDictionaryTerm.source_term.like(like))
            | (DomainDictionaryTerm.target_term.like(like))
        )
    return q.order_by(DomainDictionaryTerm.id.desc()).offset(skip).limit(limit).all()


@router.post("/{dictionary_id}/terms", response_model=DomainDictionaryTermResponse)
async def create_term(
    dictionary_id: int,
    request: DomainDictionaryTermCreate,
    db: Session = Depends(get_db),
):
    dic = db.query(DomainDictionary).filter(DomainDictionary.id == dictionary_id).first()
    if not dic:
        raise HTTPException(status_code=404, detail="词典不存在")
    source = request.source_term.strip()
    dup = (
        db.query(DomainDictionaryTerm)
        .filter(
            DomainDictionaryTerm.dictionary_id == dictionary_id,
            DomainDictionaryTerm.source_term == source,
        )
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="同源词条已存在")
    term = DomainDictionaryTerm(
        dictionary_id=dictionary_id,
        source_term=source,
        target_term=request.target_term.strip(),
        aliases=_normalize_aliases(request.aliases),
        category=request.category,
        description=request.description,
        priority=int(request.priority or 0),
    )
    db.add(term)
    db.flush()
    _refresh_term_count(db, dictionary_id)
    db.commit()
    db.refresh(term)
    return term


@router.put("/{dictionary_id}/terms/{term_id}", response_model=DomainDictionaryTermResponse)
async def update_term(
    dictionary_id: int,
    term_id: int,
    request: DomainDictionaryTermUpdate,
    db: Session = Depends(get_db),
):
    term = (
        db.query(DomainDictionaryTerm)
        .filter(
            DomainDictionaryTerm.id == term_id,
            DomainDictionaryTerm.dictionary_id == dictionary_id,
        )
        .first()
    )
    if not term:
        raise HTTPException(status_code=404, detail="词条不存在")
    fields = getattr(request, "model_fields_set", None) or set()
    if "source_term" in fields and request.source_term:
        new_source = request.source_term.strip()
        dup = (
            db.query(DomainDictionaryTerm)
            .filter(
                DomainDictionaryTerm.dictionary_id == dictionary_id,
                DomainDictionaryTerm.source_term == new_source,
                DomainDictionaryTerm.id != term_id,
            )
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="同源词条已存在")
        term.source_term = new_source
    if "target_term" in fields and request.target_term:
        term.target_term = request.target_term.strip()
    if "aliases" in fields:
        term.aliases = _normalize_aliases(request.aliases)
    if "category" in fields:
        term.category = request.category
    if "description" in fields:
        term.description = request.description
    if "priority" in fields and request.priority is not None:
        term.priority = int(request.priority)
    db.commit()
    db.refresh(term)
    return term


@router.delete("/{dictionary_id}/terms/{term_id}")
async def delete_term(dictionary_id: int, term_id: int, db: Session = Depends(get_db)):
    term = (
        db.query(DomainDictionaryTerm)
        .filter(
            DomainDictionaryTerm.id == term_id,
            DomainDictionaryTerm.dictionary_id == dictionary_id,
        )
        .first()
    )
    if not term:
        raise HTTPException(status_code=404, detail="词条不存在")
    db.delete(term)
    db.flush()
    _refresh_term_count(db, dictionary_id)
    db.commit()
    return {"message": "已删除"}


def _parse_csv_bytes(data: bytes) -> List[dict]:
    # 尝试 utf-8-sig / utf-8 / gbk
    text = None
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="无法解码 CSV，请使用 UTF-8 或 GBK")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV 缺少表头")
    return [dict(row) for row in reader]


def _parse_xlsx_bytes(data: bytes) -> List[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="服务器未安装 openpyxl，无法解析 XLSX。请 pip install openpyxl",
        ) from e
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise HTTPException(status_code=400, detail="XLSX 为空")
    headers = [str(h).strip() if h is not None else "" for h in header_row]
    if not any(headers):
        raise HTTPException(status_code=400, detail="XLSX 缺少表头")
    out: List[dict] = []
    for row in rows_iter:
        item = {}
        empty = True
        for i, h in enumerate(headers):
            if not h:
                continue
            val = row[i] if i < len(row) else None
            if val is not None and str(val).strip():
                empty = False
            item[h] = "" if val is None else str(val).strip()
        if not empty:
            out.append(item)
    return out


def _map_row(row: dict) -> Optional[dict]:
    """将一行映射为 source/target/...；兼容中英文表头。"""
    lower_map = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    aliases_keys = ("aliases", "alias", "异写", "缩写", "别名")
    category_keys = ("category", "分类", "类别")
    desc_keys = ("description", "desc", "备注", "说明")
    priority_keys = ("priority", "优先级")
    source_keys = ("source_term", "source", "原文", "源词", "术语", "term")
    target_keys = ("target_term", "target", "译文", "译名", "翻译")

    def pick(keys):
        for k in keys:
            if k in lower_map and str(lower_map[k]).strip():
                return str(lower_map[k]).strip()
        return ""

    source = pick(source_keys)
    target = pick(target_keys)
    # 若只有两列且无标准头，尝试 values 顺序
    if not source or not target:
        vals = [str(v).strip() for v in row.values() if v is not None and str(v).strip()]
        if len(vals) >= 2 and not source:
            source, target = vals[0], vals[1]
    if not source or not target:
        return None
    priority_raw = pick(priority_keys)
    try:
        priority = int(float(priority_raw)) if priority_raw else 0
    except ValueError:
        priority = 0
    return {
        "source_term": source,
        "target_term": target,
        "aliases": _normalize_aliases(pick(aliases_keys)),
        "category": pick(category_keys) or None,
        "description": pick(desc_keys) or None,
        "priority": priority,
    }


@router.post("/{dictionary_id}/import")
async def import_terms(
    dictionary_id: int,
    file: UploadFile = File(...),
    on_duplicate: str = Form("skip"),  # skip | overwrite
    db: Session = Depends(get_db),
):
    dic = db.query(DomainDictionary).filter(DomainDictionary.id == dictionary_id).first()
    if not dic:
        raise HTTPException(status_code=404, detail="词典不存在")
    if on_duplicate not in ("skip", "overwrite"):
        raise HTTPException(status_code=400, detail="on_duplicate 必须是 skip 或 overwrite")

    filename = (file.filename or "").lower()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")

    if filename.endswith(".csv"):
        raw_rows = _parse_csv_bytes(data)
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        if filename.endswith(".xls") and not filename.endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="暂不支持 .xls，请另存为 .xlsx 或 .csv")
        raw_rows = _parse_xlsx_bytes(data)
    else:
        raise HTTPException(status_code=400, detail="仅支持 CSV / XLSX")

    created = updated = skipped = invalid = 0
    for raw in raw_rows:
        mapped = _map_row(raw)
        if not mapped:
            invalid += 1
            continue
        existing = (
            db.query(DomainDictionaryTerm)
            .filter(
                DomainDictionaryTerm.dictionary_id == dictionary_id,
                DomainDictionaryTerm.source_term == mapped["source_term"],
            )
            .first()
        )
        if existing:
            if on_duplicate == "overwrite":
                existing.target_term = mapped["target_term"]
                existing.aliases = mapped["aliases"]
                existing.category = mapped["category"]
                existing.description = mapped["description"]
                existing.priority = mapped["priority"]
                updated += 1
            else:
                skipped += 1
            continue
        db.add(
            DomainDictionaryTerm(
                dictionary_id=dictionary_id,
                source_term=mapped["source_term"],
                target_term=mapped["target_term"],
                aliases=mapped["aliases"],
                category=mapped["category"],
                description=mapped["description"],
                priority=mapped["priority"],
            )
        )
        created += 1

    db.flush()
    _refresh_term_count(db, dictionary_id)
    dic.source = "upload"
    db.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "invalid": invalid,
        "term_count": dic.term_count,
    }
