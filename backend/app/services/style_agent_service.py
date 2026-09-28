"""系统级文风智能体：预设、CRUD、从文本提炼、编译风格块。"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import WritingStyleAgent

FOLLOW = "跟随原文"

DEFAULT_CONFIG: Dict[str, Any] = {
    "sentence": FOLLOW,
    "diction": FOLLOW,
    "idiom": FOLLOW,
    "register": FOLLOW,
    "compactness": FOLLOW,
    "taboo": [],
    "custom_text": "",
    "samples": [],
}

SENTENCE_OPTIONS = (FOLLOW, "多用短句", "多用长句", "长短交错")
DICTION_OPTIONS = (FOLLOW, "白话直译", "书面典雅", "口语自然")
IDIOM_OPTIONS = (FOLLOW, "少用成语", "适度成语", "多用成语")
REGISTER_OPTIONS = (FOLLOW, "偏口语", "偏书面")
COMPACT_OPTIONS = (FOLLOW, "更紧凑", "更舒缓")

_LEGACY_SENTENCE = {"短句为主": "多用短句", "长句可多": "多用长句", "长短交错": "长短交错"}
_LEGACY_DICTION = {
    "白话": "白话直译",
    "白话精简": "白话直译",
    "口语": "口语自然",
    "书面": "书面典雅",
    "略带文学性": "书面典雅",
}
_LEGACY_COMPACT = {"紧凑": "更紧凑", "轻快": "更紧凑", "舒缓": "更舒缓", "适中": FOLLOW}

STYLE_PRESETS: List[Dict[str, Any]] = [
    {
        "key": "follow_source",
        "name": "贴原文",
        "description": "尽量复现原文语气与节奏，不加额外译法",
        "config": deepcopy(DEFAULT_CONFIG),
    },
    {
        "key": "idiom_polish",
        "name": "成语工整",
        "description": "贴合原文气质，译文可多用成语、四字结构",
        "config": {
            **deepcopy(DEFAULT_CONFIG),
            "idiom": "多用成语",
            "diction": "书面典雅",
            "register": "偏书面",
            "custom_text": "在不改变原文语气的前提下，适当使用成语、四字短语，使译文更凝练。原文若本就口语、俚俗，不要硬套文言成语。",
        },
    },
    {
        "key": "short_sentence",
        "name": "短句利落",
        "description": "贴合原文，译文多用短句，节奏更干脆",
        "config": {
            **deepcopy(DEFAULT_CONFIG),
            "sentence": "多用短句",
            "compactness": "更紧凑",
            "custom_text": "在保留原文信息与语气的前提下，把长句拆成短句，少用从句堆叠。原文若本就舒缓绵长，不要切得支离破碎。",
        },
    },
    {
        "key": "literary_formal",
        "name": "书面典雅",
        "description": "贴合原文，译文偏书面、用词更考究",
        "config": {
            **deepcopy(DEFAULT_CONFIG),
            "diction": "书面典雅",
            "register": "偏书面",
            "idiom": "适度成语",
            "taboo": ["网络口语", "网络烂梗"],
            "custom_text": "用词偏书面，句式整齐，可适度用成语。原文若是口语对话，对话部分仍须保持口语，不要整篇掉书袋。",
        },
    },
    {
        "key": "colloquial",
        "name": "口语自然",
        "description": "贴合原文，译文像人说话，少文言腔",
        "config": {
            **deepcopy(DEFAULT_CONFIG),
            "diction": "口语自然",
            "register": "偏口语",
            "idiom": "少用成语",
            "sentence": "多用短句",
            "taboo": ["掉书袋", "堆砌成语"],
            "custom_text": "译文读起来像目标语言里的口头表达。原文若典雅庄重，不要改成大白话。",
        },
    },
    {
        "key": "tech_precise",
        "name": "专业克制",
        "description": "适合科技、法律、医学：贴原文、少修辞、术语稳定",
        "config": {
            **deepcopy(DEFAULT_CONFIG),
            "diction": "白话直译",
            "register": "偏书面",
            "idiom": "少用成语",
            "taboo": ["文学性比喻", "口语化修辞", "夸张形容"],
            "custom_text": "优先准确与术语统一。不因个人文采改写信息结构；原文有的修饰才保留，没有的不要添。",
        },
    },
]

EXTRACT_SYSTEM_PROMPT = """你是翻译风格分析专家。给定的材料是译者认可的「译文范例」（也可能夹杂原文）。
请提炼可复用的「译者习惯」，而不是去规定原文该长成什么样。
只输出一个 JSON 对象，不要 markdown 代码块，不要解释。字段如下：
{
  "name": "不超过12字的风格名",
  "description": "一句话：在贴合原文的前提下，这位译者习惯怎样译",
  "sentence": "跟随原文 / 多用短句 / 多用长句 / 长短交错",
  "diction": "跟随原文 / 白话直译 / 书面典雅 / 口语自然",
  "idiom": "跟随原文 / 少用成语 / 适度成语 / 多用成语",
  "register": "跟随原文 / 偏口语 / 偏书面",
  "compactness": "跟随原文 / 更紧凑 / 更舒缓",
  "taboo": ["该译法应避免的写法，1-5条"],
  "custom_text": "80-200字：说明这些习惯如何叠加在原文风格之上，以及何时必须让路给原文",
  "samples": ["从材料中摘取的译文短句1（40-120字）", "范例2", "范例3"]
}
要求：samples 尽量摘自材料中的译文；不要编造；JSON 合法。
若材料看不出某项偏好，对应字段填「跟随原文」。"""


def _pick_option(value: Any, options: Tuple[str, ...], legacy_map: Optional[Dict[str, str]] = None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return FOLLOW
    if raw in options:
        return raw
    if legacy_map and raw in legacy_map:
        mapped = legacy_map[raw]
        return mapped if mapped in options else FOLLOW
    return FOLLOW


def _normalize_config(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = deepcopy(DEFAULT_CONFIG)
    if not isinstance(raw, dict):
        return cfg

    cfg["sentence"] = _pick_option(raw.get("sentence"), SENTENCE_OPTIONS, _LEGACY_SENTENCE)
    cfg["diction"] = _pick_option(raw.get("diction"), DICTION_OPTIONS, _LEGACY_DICTION)
    cfg["idiom"] = _pick_option(raw.get("idiom"), IDIOM_OPTIONS)
    cfg["register"] = _pick_option(raw.get("register"), REGISTER_OPTIONS)
    cfg["compactness"] = _pick_option(
        raw.get("compactness") or raw.get("pace"),
        COMPACT_OPTIONS,
        _LEGACY_COMPACT,
    )
    for key in ("taboo", "samples"):
        val = raw.get(key)
        if isinstance(val, list):
            cfg[key] = [str(x).strip() for x in val if str(x).strip()]
        elif isinstance(val, str) and val.strip():
            sep = "\n\n" if key == "samples" else "\n"
            cfg[key] = [line.strip() for line in val.split(sep) if line.strip()]
    if raw.get("custom_text") is not None:
        cfg["custom_text"] = str(raw.get("custom_text") or "")
    return cfg


def compile_style_block(name: str, config: Dict[str, Any], description: str = "") -> str:
    """把翻译风格编译成注入 prompt 的风格块：先贴原文，再叠加译者习惯。"""
    cfg = _normalize_config(config)
    lines = [f"【翻译风格：{name}】"]
    if description:
        lines.append(f"定位：{description}")
    lines.append(
        "原则：先识别并复现原文的语气、节奏、语体与句式层次；"
        "下列「译者习惯」只能在贴合原文之后叠加，不能覆盖或改写原文气质。"
        "习惯与原文冲突时，以原文为准。"
    )
    habits = []
    if cfg.get("sentence") and cfg["sentence"] != FOLLOW:
        habits.append(f"句式：{cfg['sentence']}")
    if cfg.get("diction") and cfg["diction"] != FOLLOW:
        habits.append(f"用词：{cfg['diction']}")
    if cfg.get("idiom") and cfg["idiom"] != FOLLOW:
        habits.append(f"成语：{cfg['idiom']}")
    if cfg.get("register") and cfg["register"] != FOLLOW:
        habits.append(f"语体：{cfg['register']}")
    if cfg.get("compactness") and cfg["compactness"] != FOLLOW:
        habits.append(f"疏密：{cfg['compactness']}")
    if habits:
        lines.append("译者习惯（叠加，不覆盖原文）：")
        lines.extend(habits)
    else:
        lines.append("译者习惯：无额外偏好，全力贴合原文。")
    taboo = cfg.get("taboo") or []
    if taboo:
        lines.append("避免：" + "；".join(taboo))
    custom = (cfg.get("custom_text") or "").strip()
    if custom:
        lines.append(f"译者补充：\n{custom}")
    samples = cfg.get("samples") or []
    if samples:
        lines.append("译文笔触参考（勿照抄，只学习惯）：")
        for i, s in enumerate(samples[:3], 1):
            lines.append(f"--- 范例{i} ---\n{s}\n---")
    lines.append("原文口语不要忽然掉书袋；原文典雅不要改成大白话。")
    return "\n".join(lines)


def _parse_json_object(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("模型未返回内容")
    m = re.search(r"\{.*\}", text, re.DOTALL)
    candidate = m.group() if m else text
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # 去掉尾随逗号再试
    cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
    obj = json.loads(cleaned)
    if not isinstance(obj, dict):
        raise ValueError("文风 JSON 解析失败")
    return obj


def _pick_representative_chunks(
    text: str,
    max_chunks: int = 8,
    chunk_size: int = 3200,
) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size * 2:
        return [text]

    pieces = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        if end < n:
            # 尽量在段落/句号处切开
            cut = text.rfind("\n\n", start + chunk_size // 2, end)
            if cut < 0:
                cut = text.rfind("。", start + chunk_size // 2, end)
            if cut > start:
                end = cut + 1
        chunk = text[start:end].strip()
        if chunk:
            pieces.append(chunk)
        start = end
    if not pieces:
        return [text[:chunk_size]]
    if len(pieces) <= max_chunks:
        return pieces
    idxs = {
        int(round(i * (len(pieces) - 1) / (max_chunks - 1)))
        for i in range(max_chunks)
    }
    return [pieces[i] for i in sorted(idxs)[:max_chunks]]


def _pick_chunks_from_sources(
    sources: List[Tuple[str, str]],
    max_chunks: int = 12,
    chunk_size: int = 3200,
) -> List[str]:
    cleaned: List[Tuple[str, str]] = []
    for name, text in sources:
        t = (text or "").strip()
        if t:
            cleaned.append(((name or "范文").strip()[:80] or "范文", t))
    if not cleaned:
        return []
    if len(cleaned) == 1:
        name, text = cleaned[0]
        chunks = _pick_representative_chunks(text, max_chunks=max_chunks, chunk_size=chunk_size)
        return [f"【来源：{name}】\n{c}" for c in chunks]

    total_len = sum(len(t) for _, t in cleaned) or 1
    quotas: List[int] = []
    remaining = max_chunks
    for i, (_, text) in enumerate(cleaned):
        if i == len(cleaned) - 1:
            q = max(1, remaining)
        else:
            q = max(1, round(max_chunks * len(text) / total_len))
            q = min(q, remaining - (len(cleaned) - i - 1))
        quotas.append(q)
        remaining -= q

    labeled: List[str] = []
    for (name, text), q in zip(cleaned, quotas):
        for c in _pick_representative_chunks(text, max_chunks=q, chunk_size=chunk_size):
            labeled.append(f"【来源：{name}】\n{c}")
    return labeled[:max_chunks]


class StyleAgentService:
    @staticmethod
    def list_presets() -> List[Dict[str, Any]]:
        return [
            {
                "key": p["key"],
                "name": p["name"],
                "description": p["description"],
                "config": _normalize_config(p.get("config")),
            }
            for p in STYLE_PRESETS
        ]

    @staticmethod
    def get_preset(key: str) -> Optional[Dict[str, Any]]:
        for p in STYLE_PRESETS:
            if p["key"] == key:
                return p
        return None

    @staticmethod
    def to_dict(agent: WritingStyleAgent) -> Dict[str, Any]:
        return {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description or "",
            "preset_key": agent.preset_key,
            "config": _normalize_config(agent.config if isinstance(agent.config, dict) else {}),
            "is_default": bool(agent.is_default),
            "source": agent.source or "manual",
            "created_at": agent.created_at,
            "updated_at": agent.updated_at,
            "compiled_preview": compile_style_block(
                agent.name,
                agent.config if isinstance(agent.config, dict) else {},
                agent.description or "",
            ),
        }

    @staticmethod
    def ensure_default_agent(db: Session) -> None:
        exists = db.query(WritingStyleAgent.id).first()
        if exists:
            return
        preset = StyleAgentService.get_preset("follow_source") or STYLE_PRESETS[0]
        agent = WritingStyleAgent(
            name=preset["name"],
            description=preset.get("description") or "",
            preset_key=preset["key"],
            config=_normalize_config(preset.get("config")),
            is_default=True,
            source="preset",
        )
        db.add(agent)
        db.commit()

    @staticmethod
    def list_agents(db: Session) -> List[WritingStyleAgent]:
        StyleAgentService.ensure_default_agent(db)
        return (
            db.query(WritingStyleAgent)
            .order_by(WritingStyleAgent.is_default.desc(), WritingStyleAgent.id.asc())
            .all()
        )

    @staticmethod
    def get_agent(db: Session, agent_id: int) -> Optional[WritingStyleAgent]:
        return db.query(WritingStyleAgent).filter(WritingStyleAgent.id == agent_id).first()

    @staticmethod
    def get_default_agent(db: Session) -> Optional[WritingStyleAgent]:
        StyleAgentService.ensure_default_agent(db)
        return (
            db.query(WritingStyleAgent)
            .filter(WritingStyleAgent.is_default == True)  # noqa: E712
            .order_by(WritingStyleAgent.id.asc())
            .first()
        )

    @staticmethod
    def _clear_defaults(db: Session) -> None:
        db.query(WritingStyleAgent).update(
            {"is_default": False}, synchronize_session=False
        )

    @staticmethod
    def create_agent(
        db: Session,
        name: str,
        description: str = "",
        config: Optional[Dict[str, Any]] = None,
        preset_key: Optional[str] = None,
        is_default: bool = False,
        source: str = "manual",
    ) -> WritingStyleAgent:
        count = db.query(WritingStyleAgent).count()
        if is_default or count == 0:
            StyleAgentService._clear_defaults(db)
            is_default = True

        agent = WritingStyleAgent(
            name=(name or "未命名风格").strip()[:100],
            description=(description or "").strip() or None,
            preset_key=preset_key,
            config=_normalize_config(config),
            is_default=is_default,
            source=source or "manual",
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def create_from_preset(
        db: Session, preset_key: str, set_default: bool = False
    ) -> WritingStyleAgent:
        preset = StyleAgentService.get_preset(preset_key)
        if not preset:
            raise ValueError(f"未知预设: {preset_key}")
        return StyleAgentService.create_agent(
            db,
            name=preset["name"],
            description=preset.get("description") or "",
            config=preset.get("config"),
            preset_key=preset["key"],
            is_default=set_default,
            source="preset",
        )

    @staticmethod
    def update_agent(
        db: Session,
        agent_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_default: Optional[bool] = None,
    ) -> WritingStyleAgent:
        agent = StyleAgentService.get_agent(db, agent_id)
        if not agent:
            raise ValueError("文风智能体不存在")
        if name is not None:
            agent.name = name.strip()[:100] or agent.name
        if description is not None:
            agent.description = description.strip() or None
        if config is not None:
            agent.config = _normalize_config(config)
        if is_default is True:
            StyleAgentService._clear_defaults(db)
            agent.is_default = True
        agent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def delete_agent(db: Session, agent_id: int) -> None:
        agent = StyleAgentService.get_agent(db, agent_id)
        if not agent:
            raise ValueError("文风智能体不存在")
        was_default = agent.is_default
        db.delete(agent)
        db.commit()
        remaining = (
            db.query(WritingStyleAgent)
            .order_by(WritingStyleAgent.id.asc())
            .all()
        )
        if was_default and remaining:
            remaining[0].is_default = True
            db.commit()
        if not remaining:
            StyleAgentService.ensure_default_agent(db)

    @staticmethod
    def set_default(db: Session, agent_id: int) -> WritingStyleAgent:
        return StyleAgentService.update_agent(db, agent_id, is_default=True)

    @staticmethod
    def resolve_style_block(
        db: Session,
        style_agent_id: Optional[int] = None,
        *,
        use_default: bool = True,
    ) -> str:
        agent: Optional[WritingStyleAgent] = None
        if style_agent_id:
            agent = StyleAgentService.get_agent(db, style_agent_id)
            # 显式指定了 ID 但已删除：不再静默回退到默认，避免“选了 A 却用了默认”
            if not agent:
                return ""
        elif use_default:
            agent = StyleAgentService.get_default_agent(db)
        if not agent:
            return ""
        return compile_style_block(
            agent.name,
            agent.config if isinstance(agent.config, dict) else {},
            agent.description or "",
        )

    @staticmethod
    async def extract_style_from_text(
        text: str = "",
        preferred_name: Optional[str] = None,
        sources: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        from app.core.ai_client import get_ai_client

        merged: List[Tuple[str, str]] = []
        if sources:
            for item in sources:
                if not item:
                    continue
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    merged.append((str(item[0] or "范文"), str(item[1] or "")))
        raw = (text or "").strip()
        if raw:
            merged.append(("粘贴文本", raw))

        merged = [(n, t.strip()) for n, t in merged if (t or "").strip()]
        total_chars = sum(len(t) for _, t in merged)
        if total_chars < 80:
            raise ValueError("文本太短，请至少提供约 80 字以上的译文范例（可多文件合计）")

        max_chunks = 12 if len(merged) > 1 else 8
        chunks = _pick_chunks_from_sources(merged, max_chunks=max_chunks, chunk_size=3200)
        if not chunks:
            raise ValueError("未能从提供的文本中采样到有效片段")

        corpus = "\n\n——片段分隔——\n\n".join(chunks)
        if len(corpus) > 30000:
            corpus = corpus[:30000]

        source_names = [n for n, _ in merged]
        user_prompt = (
            "请综合分析以下译文范例（可能来自多个文件/片段），"
            "提炼「在贴合原文前提下的译者习惯」JSON。\n"
            "不要把原文作者的叙事视角、情节设定当成译者习惯。\n"
            f"来源数量：{len(merged)}；采样片段：{len(chunks)}。\n\n"
            f"{corpus}"
        )
        if preferred_name:
            user_prompt += f"\n\n若合适，name 优先使用：{preferred_name}"

        client = get_ai_client()
        reply = await client.chat_completion(
            [
                {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2500,
            temperature=0.3,
        )
        data = _parse_json_object(reply)

        name = (preferred_name or data.get("name") or "提炼文风").strip()[:100]
        description = str(data.get("description") or "从范文自动提炼").strip()
        if len(merged) > 1 and "多" not in description and "综合" not in description:
            description = f"综合 {len(merged)} 份范文提炼。{description}"
        config = _normalize_config(data)
        return {
            "name": name,
            "description": description,
            "config": config,
            "compiled_preview": compile_style_block(name, config, description),
            "source_chunks": len(chunks),
            "source_files": len(merged),
            "source_names": source_names[:20],
        }
