"""术语命中表单测（不依赖数据库）"""

from app.services.term_hit_service import (
    TermCandidate,
    clamp_max_entries,
    format_term_hit_table,
    match_terms_in_text,
    normalize_term_key,
)


def test_normalize_and_clamp():
    assert normalize_term_key("  Foo Bar ") == "foo bar"
    assert clamp_max_entries(None) == 40
    assert clamp_max_entries(5) == 10
    assert clamp_max_entries(999) == 200


def test_match_english_word_boundary():
    cands = [
        TermCandidate("API", "应用程序接口", "专业词典·Tech", 1),
        TermCandidate("AP", "错误短词", "系统大词库", 3),
    ]
    hits, omitted = match_terms_in_text("Call the API endpoint now.", cands, max_entries=40)
    assert omitted == 0
    assert len(hits) == 1
    assert hits[0].target_term == "应用程序接口"


def test_priority_domain_over_experience():
    cands = [
        TermCandidate("invoice", "发票", "本篇小词库", 2),
        TermCandidate("invoice", "商业发票", "专业词典·Trade", 1, bind_order=0),
    ]
    hits, _ = match_terms_in_text("Please send the invoice today.", cands)
    assert len(hits) == 1
    assert hits[0].target_term == "商业发票"
    assert "专业词典" in hits[0].source_label


def test_cjk_longest_match():
    cands = [
        TermCandidate("合同", "contract", "系统大词库", 3),
        TermCandidate("劳动合同", "labor contract", "专业词典·Legal", 1),
    ]
    hits, _ = match_terms_in_text("签署劳动合同后生效。", cands)
    assert len(hits) == 1
    assert hits[0].source_term == "劳动合同"


def test_domain_alias_beats_longer_experience_source():
    cands = [
        TermCandidate(
            "WTO",
            "世贸组织",
            "专业词典·Trade",
            1,
            aliases=("World Trade Organization",),
        ),
        TermCandidate(
            "World Trade Organization",
            "世界贸易机构",
            "本篇小词库",
            2,
        ),
    ]
    hits, _ = match_terms_in_text(
        "The World Trade Organization met today.", cands
    )
    assert len(hits) == 1
    assert hits[0].target_term == "世贸组织"


def test_max_entries_omitted():
    cands = [
        TermCandidate(f"term{i}", f"译{i}", "本篇小词库", 2)
        for i in range(5)
    ]
    text = " ".join(f"term{i}" for i in range(5))
    hits, omitted = match_terms_in_text(text, cands, max_entries=10)  # clamps to min 10, so all fit
    assert omitted == 0
    assert len(hits) == 5

    # Force a tiny limit via direct slice behavior: clamp raises min to 10,
    # so craft more than 10 terms.
    cands2 = [
        TermCandidate(f"word{i}", f"w{i}", "本篇小词库", 2)
        for i in range(15)
    ]
    text2 = " ".join(f"word{i}" for i in range(15))
    hits2, omitted2 = match_terms_in_text(text2, cands2, max_entries=10)
    assert len(hits2) == 10
    assert omitted2 == 5
    table = format_term_hit_table(hits2, omitted=omitted2)
    assert "术语命中表" in table
    assert "另有 5 条" in table
