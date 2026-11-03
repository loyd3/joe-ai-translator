"""把上传的纯文本字节解码成字符串。

中文 TXT 常见编码是 UTF-8、GB18030/GBK（Windows 记事本「ANSI」）和 UTF-16
（记事本「Unicode」）。只按 UTF-8 解，或在失败后无条件用 latin-1，都会得到乱码。
合法 UTF-8 直接采用：GB18030 往往也能解开这些字节，但会把「测试」读成更长的乱码。
"""
from __future__ import annotations

# 高频汉字（简体 + 对应繁体）。正确解码里这些字远多于误读出的生僻字。
_COMMON_CJK = frozenset(
    "的一是不了人我在有他这为之大来以个中上们到说时要就出会也你对生能而子那得于着下"
    "自之年过发后作里用道行所然家种事成方多经么去法学如都同现当没动面起看定天分还进"
    "好小部其些主样理心她本前开但因只从想实日者意无力它与长把机十民第公此已工使性高"
    "少正东文国学点问没从对会本"
    "這為與時對會來們過還進從說後發經開於裡點國學樣現當沒動種問對會個為與"
)

# (编码, 同分时的优先级，数字大的优先)
_FALLBACK_ENCODINGS = (
    ("gb18030", 3),
    ("big5", 2),
    ("utf-16-le", 1),
    ("utf-16-be", 0),
)


def decode_text_bytes(content: bytes) -> str:
    """在 UTF-8、GB18030、Big5、UTF-16 中选出可读的一种。"""
    if not content:
        return ""

    bom = _decode_bom(content)
    if bom is not None:
        return bom

    try:
        utf8 = content.decode("utf-8")
    except UnicodeDecodeError:
        utf8 = None

    # 合法 UTF-8 且没有 NUL：直接采用。
    # GB18030 经常也能解开同一段字节，但会把「测试」读成更长的乱码。
    # 记事本「Unicode」带 BOM，已在上面处理；没有 BOM、又恰好全部落在 ASCII 字节里的
    # 极短 UTF-16 与英文无法区分，这时保持 UTF-8。
    if utf8 is not None and "\x00" not in utf8:
        return utf8

    ranked: list[tuple[float, int, str]] = []
    if utf8 is not None:
        ranked.append((_quality(utf8), 4, utf8))
    for encoding, priority in _FALLBACK_ENCODINGS:
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        ranked.append((_quality(text), priority, text))

    if not ranked:
        return content.decode("utf-8", errors="replace")

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return ranked[0][2].lstrip("\ufeff")


def _decode_bom(content: bytes) -> str | None:
    if content.startswith(b"\xef\xbb\xbf"):
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return None
    if content.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        try:
            return content.decode("utf-32").lstrip("\ufeff")
        except UnicodeDecodeError:
            return None
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return content.decode("utf-16").lstrip("\ufeff")
        except UnicodeDecodeError:
            return None
    return None


def _quality(text: str) -> float:
    """按密度计分，避免「字数更多的误读」压过正确解码。"""
    if not text:
        return 0.0
    sample = text[:20000]
    common = cjk = latin = private = controls = 0
    for ch in sample:
        code = ord(ch)
        if ch in "\n\r\t ":
            latin += 1
        elif code < 32 or code == 0xFFFD:
            controls += 1
        elif "\u4e00" <= ch <= "\u9fff":
            cjk += 1
            if ch in _COMMON_CJK:
                common += 1
        elif "\ue000" <= ch <= "\uf8ff":
            private += 1
        elif code < 128:
            latin += 1
    n = len(sample)
    return (common * 8 + cjk * 0.15 + latin * 0.35 - private * 8 - controls * 12) / n
