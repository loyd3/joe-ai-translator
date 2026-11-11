"""
术语命中表：按段匹配专业词典 + 经验词库，供四步翻译注入。

优先级：专业词典(L1) > 本篇小词库(L2) > 系统大词库(L3)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.models import (
    AIConfig,
    DomainDictionary,
    DomainDictionaryTerm,
    LiteraryTranslation,
    ProfessionalTerm,
)

DEFAULT_MAX_ENTRIES = 40
MIN_MAX_ENTRIES = 10
MAX_MAX_ENTRIES = 200

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


@dataclass(frozen=True)
class TermCandidate:
    source_term: str
    target_term: str
    source_label: str  # e.g. 专业词典·ISO医疗 / 本篇小词库 / 系统大词库
    layer: int  # 1=domain, 2=doc, 3=global
    bind_order: int = 0  # lower wins within L1
    priority: int = 0  # higher wins within same dict
    usage_count: int = 0
    is_verified: bool = True
    updated_ts: float = 0.0
    aliases: Tuple[str, ...] = ()


def normalize_term_key(term: str) -> str:
    return " ".join((term or "").strip().lower().split())


def clamp_max_entries(value: Optional[int]) -> int:
    if value is None:
        return DEFAULT_MAX_ENTRIES
    try:
        n = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_ENTRIES
    return max(MIN_MAX_ENTRIES, min(MAX_MAX_ENTRIES, n))


def get_term_hit_max_entries(db: Session) -> int:
    cfg = db.query(AIConfig).filter(AIConfig.id == 1).first()
    raw = getattr(cfg, "term_hit_table_max_entries", None) if cfg else None
    return clamp_max_entries(raw)


def resolve_default_dictionary_ids(
    db: Session,
    *,
    literary_type: str,
    source_lang: str,
    target_lang: str,
) -> List[int]:
    """领域默认自动挂：同语言对 + (同领域或通用) + active + is_default_for_domain。"""
    rows = (
        db.query(DomainDictionary)
        .filter(
            DomainDictionary.is_active.is_(True),
            DomainDictionary.is_default_for_domain.is_(True),
            DomainDictionary.source_lang == source_lang,
            DomainDictionary.target_lang == target_lang,
        )
        .order_by(DomainDictionary.id.asc())
        .all()
    )
    lit = (literary_type or "general").strip()
    ids: List[int] = []
    for row in rows:
        dtype = (row.literary_type or "").strip()
        if not dtype or dtype == lit or dtype == "general":
            ids.append(row.id)
    return ids


def _is_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _find_match_span(haystack: str, needle: str) -> Optional[Tuple[int, int]]:
    """在原文中查找 needle；拉丁词用词边界，含 CJK 用直接包含。返回 (start, end)。"""
    if not haystack or not needle:
        return None
    if _is_cjk(needle) or _is_cjk(haystack):
        idx = haystack.find(needle)
        if idx < 0:
            # 再试忽略大小写（对英文混排）
            lower_h, lower_n = haystack.lower(), needle.lower()
            idx = lower_h.find(lower_n)
            if idx < 0:
                return None
            return idx, idx + len(needle)
        return idx, idx + len(needle)

    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(needle)}(?![A-Za-z0-9_])", re.IGNORECASE)
    m = pattern.search(haystack)
    if not m:
        return None
    return m.start(), m.end()


def _candidate_sort_key(c: TermCandidate) -> Tuple:
    """越小越优先（用于同规范化 key 裁决）。"""
    return (
        c.layer,
        c.bind_order,
        -c.priority,
        -len(c.source_term or ""),
        -int(c.is_verified),
        -c.usage_count,
        -c.updated_ts,
    )


def _pick_winners(candidates: Sequence[TermCandidate]) -> Dict[str, TermCandidate]:
    """同源词（含 aliases）归一化后只留一条；专业词典层优先。"""
    winners: Dict[str, TermCandidate] = {}
    for c in candidates:
        keys = [normalize_term_key(c.source_term)]
        keys.extend(normalize_term_key(a) for a in c.aliases)
        for key in keys:
            if not key:
                continue
            prev = winners.get(key)
            if prev is None or _candidate_sort_key(c) < _candidate_sort_key(prev):
                winners[key] = c
    # 同一候选可能被多个 key 指向；按对象去重后再按 source_term 建索引
    unique: Dict[int, TermCandidate] = {}
    for c in winners.values():
        unique[id(c)] = c
    by_source: Dict[str, TermCandidate] = {}
    for c in unique.values():
        key = normalize_term_key(c.source_term)
        if not key:
            continue
        prev = by_source.get(key)
        if prev is None or _candidate_sort_key(c) < _candidate_sort_key(prev):
            by_source[key] = c
    return by_source


def match_terms_in_text(
    text: str,
    candidates: Sequence[TermCandidate],
    *,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> Tuple[List[TermCandidate], int]:
    """
    在原文中命中候选词条；重叠时优先更高优先级层，其次更长匹配。
    返回 (命中列表, 因上限被丢弃的条数)。
    """
    winners = _pick_winners(candidates)
    if not winners or not (text or "").strip():
        return [], 0

    scored: List[Tuple[TermCandidate, Tuple[int, int]]] = []
    for cand in winners.values():
        needles = (cand.source_term, *cand.aliases)
        best_span: Optional[Tuple[int, int]] = None
        for needle in needles:
            n = (needle or "").strip()
            if not n:
                continue
            span = _find_match_span(text, n)
            if span is None:
                continue
            if best_span is None or (span[1] - span[0]) > (best_span[1] - best_span[0]):
                best_span = span
        if best_span is not None:
            scored.append((cand, best_span))

    # 层优先，再比匹配跨度，避免经验长词压过专业词典短 canonical + 长 alias
    scored.sort(
        key=lambda item: (
            item[0].layer,
            -(item[1][1] - item[1][0]),
            item[0].bind_order,
            -item[0].priority,
            -len(item[0].source_term or ""),
        )
    )

    occupied: List[Tuple[int, int]] = []
    hits: List[TermCandidate] = []

    def overlaps(span: Tuple[int, int]) -> bool:
        a, b = span
        for x, y in occupied:
            if a < y and b > x:
                return True
        return False

    for cand, span in scored:
        if overlaps(span):
            continue
        occupied.append(span)
        hits.append(cand)

    hits.sort(key=lambda c: next(
        (
            sp[0]
            for needle in (c.source_term, *c.aliases)
            if (sp := _find_match_span(text, (needle or "").strip()))
        ),
        10**9,
    ))
    limit = clamp_max_entries(max_entries)
    if len(hits) <= limit:
        return hits, 0
    return hits[:limit], len(hits) - limit


def format_term_hit_table(
    hits: Sequence[TermCandidate],
    *,
    omitted: int = 0,
) -> str:
    if not hits:
        return ""
    lines = [
        "## 术语命中表（必须遵守；冲突时以上表为准）",
        "以下术语在译文中必须使用指定译名；未列出的术语再参考经验与常识。",
        "",
        "| 原文 | 指定译名 | 来源 |",
        "| --- | --- | --- |",
    ]
    for h in hits:
        src = (h.source_term or "").replace("|", "\\|").strip()
        tgt = (h.target_term or "").replace("|", "\\|").strip()
        label = (h.source_label or "").replace("|", "\\|").strip()
        lines.append(f"| {src} | {tgt} | {label} |")
    if omitted > 0:
        lines.append("")
        lines.append(f"（本段另有 {omitted} 条命中因上限未注入）")
    return "\n".join(lines)


def _ts(dt) -> float:
    if not dt:
        return 0.0
    try:
        return float(dt.timestamp())
    except Exception:
        return 0.0


def _load_domain_candidates(
    db: Session,
    dictionary_ids: Sequence[int],
) -> List[TermCandidate]:
    if not dictionary_ids:
        return []
    dict_rows = (
        db.query(DomainDictionary)
        .filter(
            DomainDictionary.id.in_(list(dictionary_ids)),
            DomainDictionary.is_active.is_(True),
        )
        .all()
    )
    dict_map = {d.id: d for d in dict_rows}
    order_map = {did: idx for idx, did in enumerate(dictionary_ids) if did in dict_map}
    if not dict_map:
        return []

    terms = (
        db.query(DomainDictionaryTerm)
        .filter(DomainDictionaryTerm.dictionary_id.in_(list(dict_map.keys())))
        .all()
    )
    out: List[TermCandidate] = []
    for t in terms:
        d = dict_map.get(t.dictionary_id)
        if not d:
            continue
        aliases: Tuple[str, ...] = ()
        raw = t.aliases
        if isinstance(raw, list):
            aliases = tuple(str(a).strip() for a in raw if str(a).strip())
        elif isinstance(raw, str) and raw.strip():
            aliases = tuple(a.strip() for a in raw.split(",") if a.strip())
        out.append(
            TermCandidate(
                source_term=t.source_term,
                target_term=t.target_term,
                source_label=f"专业词典·{d.name}",
                layer=1,
                bind_order=order_map.get(t.dictionary_id, 999),
                priority=int(t.priority or 0),
                aliases=aliases,
            )
        )
    return out


def _load_experience_candidates(
    db: Session,
    translation: LiteraryTranslation,
) -> List[TermCandidate]:
    lit = translation.literary_type
    src = translation.source_lang
    tgt = translation.target_lang
    tid = translation.id

    doc_terms = (
        db.query(ProfessionalTerm)
        .filter(
            ProfessionalTerm.translation_id == tid,
            ProfessionalTerm.source_lang == src,
            ProfessionalTerm.target_lang == tgt,
        )
        .all()
    )
    global_terms = (
        db.query(ProfessionalTerm)
        .filter(
            ProfessionalTerm.translation_id.is_(None),
            ProfessionalTerm.literary_type == lit,
            ProfessionalTerm.source_lang == src,
            ProfessionalTerm.target_lang == tgt,
        )
        .all()
    )

    out: List[TermCandidate] = []
    for t in doc_terms:
        out.append(
            TermCandidate(
                source_term=t.source_term,
                target_term=t.target_term,
                source_label="本篇小词库",
                layer=2,
                is_verified=bool(t.is_verified),
                usage_count=int(t.usage_count or 0),
                updated_ts=_ts(t.updated_at or t.created_at),
            )
        )
    for t in global_terms:
        out.append(
            TermCandidate(
                source_term=t.source_term,
                target_term=t.target_term,
                source_label="系统大词库",
                layer=3,
                is_verified=bool(t.is_verified),
                usage_count=int(t.usage_count or 0),
                updated_ts=_ts(t.updated_at or t.created_at),
            )
        )
    return out


def collect_candidates_for_translation(
    db: Session,
    translation: LiteraryTranslation,
    *,
    use_domain: bool = True,
    use_experience: bool = True,
) -> List[TermCandidate]:
    candidates: List[TermCandidate] = []
    if use_domain:
        ids = list(getattr(translation, "domain_dictionary_ids", None) or [])
        candidates.extend(_load_domain_candidates(db, ids))
    if use_experience:
        candidates.extend(_load_experience_candidates(db, translation))
    return candidates


def build_term_hit_table(
    db: Session,
    translation: LiteraryTranslation,
    paragraph_text: str,
    *,
    max_entries: Optional[int] = None,
    use_domain: bool = True,
    use_experience: bool = True,
) -> str:
    limit = clamp_max_entries(max_entries if max_entries is not None else get_term_hit_max_entries(db))
    candidates = collect_candidates_for_translation(
        db, translation, use_domain=use_domain, use_experience=use_experience
    )
    hits, omitted = match_terms_in_text(paragraph_text or "", candidates, max_entries=limit)
    return format_term_hit_table(hits, omitted=omitted)


def merge_guidance_with_term_hits(
    guidance: str,
    term_hit_table: str,
) -> str:
    parts: List[str] = []
    if term_hit_table and term_hit_table.strip():
        parts.append(term_hit_table.strip())
    if guidance and guidance.strip():
        parts.append(guidance.strip())
    return "\n\n".join(parts)


def collect_hits_for_texts(
    db: Session,
    translation: LiteraryTranslation,
    texts: Sequence[str],
    *,
    max_entries: Optional[int] = None,
) -> Tuple[List[TermCandidate], int]:
    """
    对多段原文分别命中后按优先级并集，再统一截断。
    用于 step4 批处理，保证与逐段命中同一裁决规则。
    """
    limit = clamp_max_entries(max_entries if max_entries is not None else get_term_hit_max_entries(db))
    candidates = collect_candidates_for_translation(db, translation)
    merged: Dict[str, TermCandidate] = {}
    for text in texts:
        hits, _ = match_terms_in_text(text or "", candidates, max_entries=MAX_MAX_ENTRIES)
        for h in hits:
            key = normalize_term_key(h.source_term)
            prev = merged.get(key)
            if prev is None or _candidate_sort_key(h) < _candidate_sort_key(prev):
                merged[key] = h
    ordered = sorted(merged.values(), key=_candidate_sort_key)
    if len(ordered) <= limit:
        return ordered, 0
    return ordered[:limit], len(ordered) - limit


def build_term_hit_table_for_texts(
    db: Session,
    translation: LiteraryTranslation,
    texts: Sequence[str],
    *,
    max_entries: Optional[int] = None,
) -> str:
    hits, omitted = collect_hits_for_texts(db, translation, texts, max_entries=max_entries)
    return format_term_hit_table(hits, omitted=omitted)
