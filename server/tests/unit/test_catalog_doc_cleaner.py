"""Unit tests for primary-source document cleaning (pure logic, no network)."""

import pytest

from app.services.catalog.doc_cleaner import (
    detect_document_kind,
    extract_sections,
    prepare_for_llm,
    truncate_to_tokens,
)


@pytest.mark.unit
def test_prepare_for_llm_strips_html_and_scripts():
    out = prepare_for_llm("<html><body><script>evil()</script><p>Hello</p><p>World</p></body></html>")
    assert "Hello" in out
    assert "World" in out
    assert "<" not in out
    assert "evil" not in out


@pytest.mark.unit
def test_detect_document_kind():
    assert detect_document_kind("Item 2.02 Results of Operations and Financial Condition") == "sec_8k"
    assert detect_document_kind("Management's Discussion and Analysis of Financial Condition") == "sec_10k"
    assert detect_document_kind("Supplementary Information: agency background") == "gov_reg"
    assert detect_document_kind("Just an ordinary blog post about coffee") is None


@pytest.mark.unit
def test_extract_sections_isolates_mda():
    text = "Preamble junk. Management's Discussion and Analysis: revenue grew. Risk Factors: rates rose."
    out = extract_sections(
        text,
        (r"Management'?s Discussion and Analysis", r"\bRisk Factors\b"),
        max_chars=1000,
    )
    assert out.startswith("Management's Discussion and Analysis")
    assert "revenue grew" in out
    assert "Risk Factors" in out
    assert "Preamble" not in out


@pytest.mark.unit
def test_truncate_to_tokens_respects_budget_on_word_boundary():
    text = "word " * 1000
    out = truncate_to_tokens(text, max_tokens=10)
    assert len(out) <= 40
    assert out.strip().endswith("word")


@pytest.mark.unit
def test_prepare_for_llm_applies_section_extraction_and_cap():
    html = "<p>Item 2.02 Results</p>" + "<p>filler</p>" * 5000
    out = prepare_for_llm(html, max_tokens=50)
    assert "Item 2.02" in out
    assert len(out) <= 50 * 4
