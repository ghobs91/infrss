"""Integration tests for the layman summary endpoints (clipped-article path)."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.article import ArticleContent, ArticleLaymanSummary, UserEntry
from app.services.ai.layman import LaymanSummaryDraft


async def _clipped_article(db_session, user):
    """Create a shared ArticleContent + the user's clipped UserEntry."""
    content = ArticleContent(
        content_hash=f"hash-{uuid4().hex}",
        title="SEC Form 8-K",
        link="https://www.sec.gov/example",
        content="<p>Item 2.02 Results of Operations</p>",
    )
    db_session.add(content)
    await db_session.flush()

    entry = UserEntry(user_id=user.id, content_id=content.id, is_saved=True)
    db_session.add(entry)
    await db_session.flush()
    await db_session.refresh(entry)
    return content, entry


@pytest.mark.asyncio
async def test_put_then_get_layman_summary(db_session, test_user, async_client):
    content, entry = await _clipped_article(db_session, test_user)
    payload = {
        "headline": "Company reports quarterly results",
        "what_happened": ["Revenue rose 10%", "Guidance raised"],
        "key_impact": "Margins improve next quarter",
        "model_identifier": "Llama-3.2-1B-Instruct",
    }

    put = await async_client.put(f"/api/articles/{entry.id}/layman-summary?clipped=true", json=payload)
    assert put.status_code == 200, put.text
    assert put.json()["headline"] == payload["headline"]

    got = await async_client.get(f"/api/articles/{entry.id}/layman-summary?clipped=true")
    assert got.status_code == 200
    assert got.json()["what_happened"] == payload["what_happened"]

    stored = (
        (await db_session.execute(select(ArticleLaymanSummary).where(ArticleLaymanSummary.content_id == content.id)))
        .scalars()
        .first()
    )
    assert stored is not None
    assert stored.model_identifier == "Llama-3.2-1B-Instruct"


@pytest.mark.asyncio
async def test_get_layman_summary_404_when_absent(db_session, test_user, async_client):
    _, entry = await _clipped_article(db_session, test_user)
    response = await async_client.get(f"/api/articles/{entry.id}/layman-summary?clipped=true")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_layman_summary_server_fallback(db_session, test_user, async_client):
    _, entry = await _clipped_article(db_session, test_user)
    draft = LaymanSummaryDraft(headline="H", what_happened=["B1"], key_impact="I")

    with patch(
        "app.routers.articles.articles_layman.generate_layman_summary",
        new=AsyncMock(return_value=draft),
    ):
        response = await async_client.post(f"/api/articles/{entry.id}/layman-summary/generate?clipped=true")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["headline"] == "H"
    assert body["what_happened"] == ["B1"]
    assert body["model_identifier"]
