"""Layman summary endpoints: plain-language translations of primary-source documents.

A client with on-device WebLLM (or a local Ollama endpoint) generates the summary and caches it
with ``PUT``; clients without one call ``POST .../generate`` for the server-side fallback. Both
write the same shared row, so one generated summary serves every user.
"""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Body, Depends, Query

from app.core.config import get_settings
from app.core.custom_exceptions import NotFoundError, ValidationError
from app.crud.article import layman as layman_crud
from app.db.session import get_db_factory
from app.models.article import ArticleLaymanSummary
from app.routers.articles.articles_enhancements import get_article_or_404, resolve_content
from app.services.ai.layman import generate_layman_summary
from app.services.feeds.service import SessionFactory
from app.services.user.auth import get_current_user
from app.services.user.resource_limits import enforce_daily_ai_limit
from app.typing.layman import LaymanSummaryRead, LaymanSummaryUpsert
from app.typing.user import TokenData

logger = structlog.get_logger(__name__)
router = APIRouter()


def _to_read(row: ArticleLaymanSummary) -> LaymanSummaryRead:
    """Serialize a stored summary row to the API schema."""
    return LaymanSummaryRead.model_validate(row, from_attributes=True)


@router.get(
    "/{article_id}/layman-summary",
    response_model=LaymanSummaryRead,
    summary="Get the stored layman summary for an article",
)
async def get_layman_summary(
    article_id: UUID,
    user: Annotated[TokenData, Depends(get_current_user)],
    db_factory: Annotated[SessionFactory, Depends(get_db_factory)],
    clipped: bool = Query(False, description="Whether the article is a clipped article"),
) -> LaymanSummaryRead:
    """Return the stored summary or 404 when none has been generated yet."""
    article = await get_article_or_404(db_factory, article_id, UUID(user.sub), is_clipped=clipped)
    if not article.content_id:
        raise NotFoundError(message="Article content not found")

    async with db_factory() as db:
        row = await layman_crud.get_by_content_id(db, content_id=article.content_id)
    if not row:
        raise NotFoundError(message="No layman summary available")
    return _to_read(row)


@router.put(
    "/{article_id}/layman-summary",
    response_model=LaymanSummaryRead,
    summary="Cache a client-generated layman summary",
)
async def put_layman_summary(
    article_id: UUID,
    payload: Annotated[LaymanSummaryUpsert, Body(...)],
    user: Annotated[TokenData, Depends(get_current_user)],
    db_factory: Annotated[SessionFactory, Depends(get_db_factory)],
    clipped: bool = Query(False, description="Whether the article is a clipped article"),
) -> LaymanSummaryRead:
    """Persist a summary produced on-device (WebLLM) or by a local Ollama endpoint."""
    article = await get_article_or_404(db_factory, article_id, UUID(user.sub), is_clipped=clipped)
    if not article.content_id:
        raise NotFoundError(message="Article content not found")

    async with db_factory() as db:
        row = await layman_crud.upsert(
            db,
            content_id=article.content_id,
            headline=payload.headline,
            what_happened=payload.what_happened,
            key_impact=payload.key_impact,
            model_identifier=payload.model_identifier,
        )
    return _to_read(row)


@router.post(
    "/{article_id}/layman-summary/generate",
    response_model=LaymanSummaryRead,
    summary="Generate a layman summary server-side (fallback)",
)
async def generate_layman_summary_endpoint(
    article_id: UUID,
    user: Annotated[TokenData, Depends(get_current_user)],
    db_factory: Annotated[SessionFactory, Depends(get_db_factory)],
    clipped: bool = Query(False, description="Whether the article is a clipped article"),
) -> LaymanSummaryRead:
    """Server-side fallback for clients without WebGPU / a local model."""
    async with db_factory() as db:
        await enforce_daily_ai_limit(db, UUID(user.sub))

    article = await get_article_or_404(db_factory, article_id, UUID(user.sub), is_clipped=clipped)
    if not article.content_id:
        raise NotFoundError(message="Article content not found")

    content = resolve_content(None, article)
    draft = await generate_layman_summary(title=article.title or "", content=content)
    if not draft:
        raise ValidationError(message="Failed to generate layman summary")

    async with db_factory() as db:
        row = await layman_crud.upsert(
            db,
            content_id=article.content_id,
            headline=draft.headline,
            what_happened=draft.what_happened,
            key_impact=draft.key_impact,
            model_identifier=get_settings().GEMINI_FAST_MODEL,
        )
    return _to_read(row)
