"""Unit tests for layman summary parsing (pure logic, no network)."""

import pytest

from app.services.ai.layman import parse_layman_summary

_VALID = '{"headline": "X", "whatHappened": ["a", "b"], "keyImpact": "Y"}'


@pytest.mark.unit
def test_parse_layman_summary_valid():
    draft = parse_layman_summary(_VALID)
    assert draft is not None
    assert draft.headline == "X"
    assert draft.what_happened == ["a", "b"]
    assert draft.key_impact == "Y"


@pytest.mark.unit
def test_parse_layman_summary_strips_markdown_fence():
    draft = parse_layman_summary(f"```json\n{_VALID}\n```")
    assert draft is not None
    assert draft.headline == "X"


@pytest.mark.unit
def test_parse_layman_summary_rejects_invalid_payloads():
    assert parse_layman_summary(None) is None
    assert parse_layman_summary("") is None
    assert parse_layman_summary("not json") is None
    assert parse_layman_summary('{"headline": "X"}') is None
    assert parse_layman_summary('{"headline": "X", "whatHappened": "nope", "keyImpact": "Y"}') is None
    assert parse_layman_summary('{"headline": "X", "whatHappened": [], "keyImpact": "Y"}') is None
