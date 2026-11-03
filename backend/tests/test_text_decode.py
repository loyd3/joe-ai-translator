"""TXT 多编码解码：GBK / UTF-16 / Big5 不能被当成 UTF-8 或 latin-1。"""
from app.core.text_decode import decode_text_bytes

SIMPLIFIED = "这是一段用于测试编码的中文文本。你好，世界。\n我们需要正确解码。"
TRADITIONAL = "這是一段用於測試編碼的中文文本。你好，世界。\n我們需要正確解碼。"


def test_utf8_simplified():
    assert decode_text_bytes(SIMPLIFIED.encode("utf-8")) == SIMPLIFIED


def test_short_utf8_words_not_read_as_gb18030():
    # 这些词的 UTF-8 字节同时是合法 GB18030，但解出来更长、是乱码。
    for word in ("测试", "价格", "翻译", "章节", "结束", "版权"):
        assert decode_text_bytes(word.encode("utf-8")) == word


def test_short_ascii_not_read_as_gbk():
    for word in ("Page", "Back", "Hello", "eg"):
        assert decode_text_bytes(word.encode("utf-8")) == word


def test_short_gbk_words():
    for word in ("测试", "价格", "翻译", "或"):
        assert decode_text_bytes(word.encode("gbk")) == word


def test_utf8_bom_is_stripped():
    raw = b"\xef\xbb\xbf" + SIMPLIFIED.encode("utf-8")
    assert decode_text_bytes(raw) == SIMPLIFIED


def test_gbk_not_mojibake():
    assert decode_text_bytes(SIMPLIFIED.encode("gbk")) == SIMPLIFIED


def test_gb18030_same_as_gbk_for_common_text():
    assert decode_text_bytes(SIMPLIFIED.encode("gb18030")) == SIMPLIFIED


def test_utf16_with_bom():
    assert decode_text_bytes(SIMPLIFIED.encode("utf-16")) == SIMPLIFIED


def test_utf16_le_without_bom():
    assert decode_text_bytes(SIMPLIFIED.encode("utf-16-le")) == SIMPLIFIED


def test_utf16_le_without_bom_needs_a_non_ascii_byte():
    # 含「的」时低字节 >= 0x80，整段不再是合法 UTF-8，应识别为 UTF-16。
    text = "你好世界的人"
    assert decode_text_bytes(text.encode("utf-16-le")) == text


def test_big5_traditional():
    assert decode_text_bytes(TRADITIONAL.encode("big5")) == TRADITIONAL


def test_plain_english_stays_utf8():
    text = "Hello world.\nThis is plain English text.\n"
    assert decode_text_bytes(text.encode("utf-8")) == text


def test_empty():
    assert decode_text_bytes(b"") == ""
