"""故事类文本的结构档案：翻译过程中增量整理，并回灌到后续翻译。"""

import json
import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.models import LiteraryTranslation, ProfessionalTerm

logger = logging.getLogger(__name__)

STORY_TYPES = {"novel", "drama", "prose", "general"}
STORY_BATCH = 5


def is_story_type(literary_type: Optional[str]) -> bool:
    return (literary_type or "") in STORY_TYPES


def empty_profile() -> dict:
    return {
        "synopsis": "",
        "characters": [],
        "relationships": [],
        "storylines": [],
        "settings": [],
        "narration": {"point_of_view": "", "tone": "", "notes": ""},
        "updated_through_index": -1,
    }


def normalize_profile(raw: Any) -> dict:
    profile = empty_profile()
    if not isinstance(raw, dict):
        return profile
    profile["synopsis"] = (raw.get("synopsis") or "").strip() if isinstance(raw.get("synopsis"), str) else ""
    profile["characters"] = [
        _normalize_character(item)
        for item in (raw.get("characters") or [])
        if isinstance(item, dict) and not _looks_like_meta_noise(item)
    ]
    profile["relationships"] = [
        _normalize_relationship(item)
        for item in (raw.get("relationships") or [])
        if isinstance(item, dict)
    ]
    profile["storylines"] = [item for item in (raw.get("storylines") or []) if isinstance(item, dict)]
    profile["settings"] = [
        item for item in (raw.get("settings") or [])
        if isinstance(item, dict) and not _looks_like_meta_noise(item)
    ]
    narration = raw.get("narration") if isinstance(raw.get("narration"), dict) else {}
    profile["narration"] = {
        "point_of_view": narration.get("point_of_view") or "",
        "tone": narration.get("tone") or "",
        "notes": narration.get("notes") or "",
    }
    try:
        profile["updated_through_index"] = int(raw.get("updated_through_index", -1))
    except (TypeError, ValueError):
        profile["updated_through_index"] = -1
    return profile


def _normalize_character(item: dict) -> dict:
    aliases = item.get("aliases") or []
    if not isinstance(aliases, list):
        aliases = []
    return {
        "name": (item.get("name") or "").strip(),
        "aliases": [str(a).strip() for a in aliases if str(a).strip()],
        "role": (item.get("role") or "").strip(),
        "portrait": (item.get("portrait") or "").strip(),
        "relations": (item.get("relations") or "").strip(),
        "translation": (item.get("translation") or "").strip(),
        "confirmed": bool(item.get("confirmed")),
        "paragraph_indexes": item.get("paragraph_indexes") or [],
    }


def _normalize_relationship(item: dict) -> dict:
    return {
        "from": (item.get("from") or item.get("source") or "").strip(),
        "to": (item.get("to") or item.get("target") or "").strip(),
        "relation": (item.get("relation") or item.get("type") or "").strip(),
    }


_META_NOISE_RE = re.compile(
    r"(出版|出版社|版权|ISBN|书评|评价|推荐语|编辑推荐|营销|广告|作者简介|装帧|定价|开本|"
    r"publisher|isbn|review|blurb|foreword by editor|copyright)",
    re.IGNORECASE,
)


def _looks_like_meta_noise(item: dict) -> bool:
    text = " ".join(
        str(item.get(k) or "") for k in ("title", "detail", "summary", "name", "role", "notes")
    )
    return bool(_META_NOISE_RE.search(text))


def lock_confirmed(previous: dict, updated: dict) -> dict:
    """用户确认过的译名不被后续梳理覆盖。"""
    confirmed = {
        (item.get("name") or "").strip(): item
        for item in previous.get("characters") or []
        if item.get("confirmed") and (item.get("name") or "").strip()
    }
    names = set()
    for item in updated.get("characters") or []:
        name = (item.get("name") or "").strip()
        names.add(name)
        locked = confirmed.get(name)
        if locked:
            item["translation"] = locked.get("translation") or item.get("translation") or ""
            item["confirmed"] = True
            if locked.get("portrait") and not item.get("portrait"):
                item["portrait"] = locked.get("portrait")
    for name, item in confirmed.items():
        if name not in names:
            updated.setdefault("characters", []).append(item)
    return updated


def format_digest(profile: Optional[dict]) -> str:
    if not profile:
        return ""
    lines = []
    synopsis = (profile.get("synopsis") or "").strip()
    if synopsis:
        lines.append(f"故事简介：{synopsis[:400]}")
    narration = profile.get("narration") or {}
    narr_bits = [bit for bit in [
        f"视角 {narration.get('point_of_view')}" if narration.get("point_of_view") else "",
        f"语气 {narration.get('tone')}" if narration.get("tone") else "",
        narration.get("notes") or "",
    ] if bit]
    if narr_bits:
        lines.append("叙述：" + "；".join(narr_bits))
    for item in profile.get("characters") or []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        translation = (item.get("translation") or "").strip()
        translated = f" → {translation}" if translation else ""
        lock = "（译名已确认，不可更改）" if item.get("confirmed") else ""
        extra = "；".join(
            bit for bit in [
                item.get("role") or "",
                item.get("portrait") or "",
                item.get("relations") or "",
            ] if bit
        )
        lines.append(f"人物：{name}{translated}{lock}" + (f"；{extra}" if extra else ""))
    for item in profile.get("relationships") or []:
        frm = (item.get("from") or "").strip()
        to = (item.get("to") or "").strip()
        rel = (item.get("relation") or "").strip()
        if frm and to and rel:
            lines.append(f"关系：{frm} —{rel}→ {to}")
    for item in profile.get("storylines") or []:
        title = item.get("title") or "故事线"
        lines.append(f"故事线：{title} — {item.get('summary') or ''}（{item.get('status') or '进行中'}）")
    for item in profile.get("settings") or []:
        title = item.get("title") or "设定"
        lines.append(f"设定：{title} — {item.get('detail') or ''}")
    return "\n".join(lines)[:2500]


def neighbor_note(paragraphs: list, index: int) -> str:
    parts = []
    if index > 0:
        prev = paragraphs[index - 1]
        prev_source = (prev.source_text or "")[:300]
        prev_trans = (prev.translated_text or prev.step1_translation or "")[:300]
        if prev_source:
            parts.append(f"上一段原文（仅供衔接，不要翻译）：{prev_source}")
        if prev_trans:
            parts.append(f"上一段译文（仅供衔接，不要翻译）：{prev_trans}")
    if index + 1 < len(paragraphs):
        nxt = (paragraphs[index + 1].source_text or "")[:300]
        if nxt:
            parts.append(f"下一段原文（仅供衔接，不要翻译）：{nxt}")
    return "\n".join(parts)


def save_profile(translation: LiteraryTranslation, profile: dict, db: Session) -> dict:
    profile = normalize_profile(profile)
    translation.story_profile = profile
    flag_modified(translation, "story_profile")
    _sync_character_terms(translation, profile, db)
    db.commit()
    db.refresh(translation)
    return profile


def _sync_character_terms(translation: LiteraryTranslation, profile: dict, db: Session) -> None:
    for item in profile.get("characters") or []:
        source_term = (item.get("name") or "").strip()
        target_term = (item.get("translation") or "").strip()
        if not source_term or not target_term:
            continue
        existing = db.query(ProfessionalTerm).filter(
            ProfessionalTerm.source_term == source_term,
            ProfessionalTerm.source_lang == translation.source_lang,
            ProfessionalTerm.target_lang == translation.target_lang,
            ProfessionalTerm.literary_type == translation.literary_type,
            ProfessionalTerm.translation_id == translation.id,
        ).first()
        description = item.get("role") or item.get("portrait") or item.get("relations") or ""
        if existing:
            if item.get("confirmed"):
                existing.target_term = target_term
                existing.category = existing.category or "人物"
                if description:
                    existing.description = description
        else:
            db.add(ProfessionalTerm(
                source_term=source_term,
                target_term=target_term,
                literary_type=translation.literary_type,
                category="人物",
                source_lang=translation.source_lang,
                target_lang=translation.target_lang,
                description=description or None,
                translation_id=translation.id,
                is_verified=bool(item.get("confirmed")),
                usage_count=1,
            ))


def _clip(text: str, limit: int = 500) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def build_batch_excerpt(paragraphs: list, include_translation: bool) -> str:
    chunks = []
    for para in paragraphs:
        block = f"【第 {para.paragraph_index + 1} 段原文】\n{_clip(para.source_text, 400)}"
        if include_translation:
            translated = para.translated_text or para.step1_translation or ""
            if translated:
                block += f"\n【第 {para.paragraph_index + 1} 段译文】\n{_clip(translated, 300)}"
        chunks.append(block)
    return "\n\n".join(chunks)[:6000]


def compact_profile_for_prompt(profile: Optional[dict], max_chars: int = 3500) -> dict:
    """压缩已有档案，避免塞进 prompt 后模型输出超长被截断。"""
    raw = normalize_profile(profile)
    compact = empty_profile()
    compact["synopsis"] = _clip(raw.get("synopsis") or "", 280)
    compact["narration"] = {
        "point_of_view": _clip((raw.get("narration") or {}).get("point_of_view") or "", 40),
        "tone": _clip((raw.get("narration") or {}).get("tone") or "", 40),
        "notes": _clip((raw.get("narration") or {}).get("notes") or "", 120),
    }
    compact["characters"] = []
    for item in (raw.get("characters") or [])[:20]:
        compact["characters"].append({
            "name": item.get("name") or "",
            "aliases": (item.get("aliases") or [])[:4],
            "role": _clip(item.get("role") or "", 60),
            "portrait": _clip(item.get("portrait") or "", 120),
            "relations": _clip(item.get("relations") or "", 80),
            "translation": item.get("translation") or "",
            "confirmed": bool(item.get("confirmed")),
            "paragraph_indexes": (item.get("paragraph_indexes") or [])[-6:],
        })
    compact["relationships"] = [
        {
            "from": e.get("from") or "",
            "to": e.get("to") or "",
            "relation": _clip(e.get("relation") or "", 40),
        }
        for e in (raw.get("relationships") or [])[:24]
        if (e.get("from") or "").strip() and (e.get("to") or "").strip()
    ]
    compact["storylines"] = [
        {
            "title": _clip(s.get("title") or "", 40),
            "summary": _clip(s.get("summary") or "", 160),
            "status": _clip(s.get("status") or "", 20),
            "paragraph_indexes": (s.get("paragraph_indexes") or [])[-6:],
        }
        for s in (raw.get("storylines") or [])[:10]
    ]
    compact["settings"] = [
        {
            "title": _clip(s.get("title") or "", 40),
            "detail": _clip(s.get("detail") or "", 120),
            "paragraph_indexes": (s.get("paragraph_indexes") or [])[-6:],
        }
        for s in (raw.get("settings") or [])[:12]
    ]
    compact["updated_through_index"] = raw.get("updated_through_index", -1)
    encoded = json.dumps(compact, ensure_ascii=False)
    if len(encoded) <= max_chars:
        return compact
    # 仍过长则再砍画像与摘要
    for item in compact["characters"]:
        item["portrait"] = _clip(item.get("portrait") or "", 60)
    for item in compact["storylines"]:
        item["summary"] = _clip(item.get("summary") or "", 80)
    compact["synopsis"] = _clip(compact.get("synopsis") or "", 160)
    return compact


def _repair_truncated_json(raw: str) -> str:
    """尽力修补因 max_tokens 截断导致的未闭合 JSON。"""
    text = (raw or "").strip()
    if not text:
        return text
    # 去掉未完成的末尾字符串字面量（停在引号内）
    in_string = False
    escape = False
    last_safe = -1
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
                last_safe = i
        else:
            if ch == '"':
                in_string = True
            elif ch in "{}[],:":
                last_safe = i
            elif ch.strip():
                last_safe = i
    if in_string and last_safe >= 0:
        text = text[: last_safe + 1]
    # 补齐括号
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack and stack[-1] == ch:
            stack.pop()
    # 去掉尾部残缺的逗号/冒号
    text = re.sub(r"[,:\s]+$", "", text)
    while stack:
        text += stack.pop()
    return text


def parse_profile_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as first_err:
        repaired = _repair_truncated_json(raw)
        try:
            data = json.loads(repaired)
            logger.warning("story profile JSON was truncated; repaired and loaded")
        except json.JSONDecodeError:
            raise ValueError(f"故事结构 JSON 解析失败（可能被模型截断）: {first_err}") from first_err
    if not isinstance(data, dict):
        raise ValueError("story profile is not an object")
    return normalize_profile(data)


async def refresh_story_profile(
    client,
    translation: LiteraryTranslation,
    batch: list,
    db: Session,
    include_translation: bool,
    preserve_empty_fields: bool = True,
) -> dict:
    if not batch or not is_story_type(translation.literary_type):
        return normalize_profile(translation.story_profile)
    previous = normalize_profile(translation.story_profile)
    excerpt = build_batch_excerpt(batch, include_translation)
    updated = await client.update_story_profile(
        literary_type=translation.literary_type,
        source_lang=translation.source_lang,
        target_lang=translation.target_lang,
        previous_profile=previous,
        excerpt=excerpt,
    )
    updated = lock_confirmed(previous, normalize_profile(updated))
    if preserve_empty_fields:
        if not (updated.get("synopsis") or "").strip() and (previous.get("synopsis") or "").strip():
            updated["synopsis"] = previous["synopsis"]
        if not updated.get("relationships") and previous.get("relationships"):
            updated["relationships"] = previous["relationships"]
    updated["updated_through_index"] = batch[-1].paragraph_index
    return save_profile(translation, updated, db)


async def regenerate_story_profile(
    client,
    translation: LiteraryTranslation,
    db: Session,
    include_translation: bool = True,
) -> dict:
    """按全部段落原文（及可选译文）从头重建故事结构；已确认译名会保留。"""
    if not is_story_type(translation.literary_type):
        raise ValueError("当前文本类型不整理故事结构")
    from app.models.models import LiteraryParagraph

    paragraphs = db.query(LiteraryParagraph).filter(
        LiteraryParagraph.translation_id == translation.id
    ).order_by(LiteraryParagraph.paragraph_index).all()
    if not paragraphs:
        raise ValueError("没有可用原文段落，无法生成故事结构")

    previous = normalize_profile(translation.story_profile)
    seed = empty_profile()
    seed["characters"] = [
        item for item in (previous.get("characters") or [])
        if item.get("confirmed") and (item.get("name") or "").strip()
    ]
    save_profile(translation, seed, db)
    db.refresh(translation)

    failures = 0
    for i in range(0, len(paragraphs), STORY_BATCH):
        batch = paragraphs[i:i + STORY_BATCH]
        try:
            await refresh_story_profile(
                client,
                translation,
                batch,
                db,
                include_translation=include_translation,
                preserve_empty_fields=False,
            )
        except Exception:
            failures += 1
            logger.exception(
                "story regenerate batch failed for translation %s at index %s",
                translation.id,
                batch[0].paragraph_index if batch else i,
            )
        db.refresh(translation)

    profile = normalize_profile(translation.story_profile)
    if failures and not (
        profile.get("synopsis")
        or profile.get("characters")
        or profile.get("storylines")
        or profile.get("settings")
        or profile.get("relationships")
    ):
        raise ValueError("重新生成失败：模型输出被截断或无效，请稍后重试")
    return profile


async def safe_refresh_story_profile(
    client,
    translation: LiteraryTranslation,
    batch: list,
    db: Session,
    include_translation: bool,
) -> dict:
    try:
        return await refresh_story_profile(client, translation, batch, db, include_translation)
    except Exception:
        logger.exception("story profile update failed for translation %s", translation.id)
        return normalize_profile(translation.story_profile)
