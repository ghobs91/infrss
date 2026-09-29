"""Reduce dense primary-source documents to a model-sized prompt.

Dense disclosures (SEC filings, regulations) exceed local LLM context windows, so before any
summarisation we strip boilerplate, isolate the load-bearing sections and cap the input. Pure and
side-effect free so the same rules are unit-testable and reusable.
"""

import re
from collections.abc import Sequence

from app.core.constants import LAYMAN_SUMMARY_CHARS_PER_TOKEN, LAYMAN_SUMMARY_MAX_INPUT_TOKENS
from app.utils.text import clean_html_text

# Heading patterns whose sections carry the substance of each document type.
SECTION_MARKERS: dict[str, tuple[str, ...]] = {
    "sec_10k": (r"Management'?s Discussion and Analysis", r"\bRisk Factors\b"),
    "sec_8k": (r"Item\s+\d\.\d{2}",),
    "gov_reg": (r"\bSupplementary Information\b", r"\bSummary\b", r"\bAction\b"),
}

# 10-K markers are checked before 8-K: an 8-K item number ("Item 2.02") is two-part, so it cannot
# false-positive on a 10-K's single-part "Item 7".
_DETECTION_ORDER = ("sec_10k", "sec_8k", "gov_reg")


def detect_document_kind(text: str) -> str | None:
    """Classify a document by the section headings it contains."""
    for kind in _DETECTION_ORDER:
        if any(re.search(marker, text, re.IGNORECASE) for marker in SECTION_MARKERS[kind]):
            return kind
    return None


def extract_sections(text: str, markers: Sequence[str], *, max_chars: int) -> str:
    """Return the concatenated spans beginning at each marker, capped at ``max_chars``."""
    pattern = re.compile("|".join(markers), re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        return text[:max_chars]

    segments: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segments.append(text[start:end].strip())
    return "\n\n".join(segments)[:max_chars]


def truncate_to_tokens(text: str, max_tokens: int, *, chars_per_token: int = LAYMAN_SUMMARY_CHARS_PER_TOKEN) -> str:
    """Truncate to an approximate token budget, cutting on a word boundary."""
    limit = max_tokens * chars_per_token
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    return cut[:last_space] if last_space > 0 else cut


def clean_document(content: str) -> str:
    """Strip HTML/boilerplate from a document to plain text."""
    return clean_html_text(content)


def prepare_for_llm(content: str, *, max_tokens: int = LAYMAN_SUMMARY_MAX_INPUT_TOKENS) -> str:
    """Clean, section-isolate and truncate a document to fit the configured prompt ceiling."""
    text = clean_document(content)
    kind = detect_document_kind(text)
    if kind:
        text = extract_sections(text, SECTION_MARKERS[kind], max_chars=max_tokens * LAYMAN_SUMMARY_CHARS_PER_TOKEN)
    return truncate_to_tokens(text, max_tokens)
