"""Server-side layman summarisation.

Fallback for clients without on-device WebLLM (no WebGPU, model not downloaded, or a failure).
Cleans and truncates the document, asks the configured LLM for the strict JSON contract, and
returns a validated draft.
"""

import json
import re
from dataclasses import dataclass

import structlog

from app.core.constants import LAYMAN_SUMMARY_MAX_OUTPUT_TOKENS, LAYMAN_SUMMARY_TEMPERATURE
from app.services.ai.client import get_gemini_client
from app.services.ai.prompts import LAYMAN_SUMMARY_SYSTEM_PROMPT
from app.services.ai.service import _call_gemini
from app.services.catalog.doc_cleaner import prepare_for_llm

logger = structlog.get_logger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass(frozen=True)
class LaymanSummaryDraft:
    """A validated layman summary before persistence."""

    headline: str
    what_happened: list[str]
    key_impact: str


def parse_layman_summary(raw: str | None) -> LaymanSummaryDraft | None:
    """Parse a model response into a draft, tolerating markdown-fenced JSON."""
    if not raw:
        return None
    cleaned = _FENCE_RE.sub("", raw.strip()).strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Layman summary response was not valid JSON")
        return None
    if not isinstance(data, dict):
        return None

    headline = data.get("headline")
    what_happened = data.get("whatHappened")
    key_impact = data.get("keyImpact")
    if not isinstance(headline, str) or not isinstance(key_impact, str):
        return None
    if not isinstance(what_happened, list) or not all(isinstance(bullet, str) for bullet in what_happened):
        return None

    bullets = [bullet.strip() for bullet in what_happened if bullet.strip()]
    if not headline.strip() or not key_impact.strip() or not bullets:
        return None
    return LaymanSummaryDraft(headline=headline.strip(), what_happened=bullets, key_impact=key_impact.strip())


async def generate_layman_summary(title: str, content: str) -> LaymanSummaryDraft | None:
    """Generate a layman summary server-side. Returns ``None`` when AI is unavailable or fails."""
    client = get_gemini_client()
    if not client:
        return None

    prepared = prepare_for_llm(content)
    prompt = f"Title: {title}\n\nDocument:\n{prepared}"
    raw = await _call_gemini(
        client,
        prompt=prompt,
        system_instruction=LAYMAN_SUMMARY_SYSTEM_PROMPT,
        max_tokens=LAYMAN_SUMMARY_MAX_OUTPUT_TOKENS,
        temperature=LAYMAN_SUMMARY_TEMPERATURE,
    )
    return parse_layman_summary(raw)
