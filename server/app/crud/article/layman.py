"""CRUD operations for article layman summaries (keyed by shared content_id)."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleLaymanSummary

logger = structlog.get_logger(__name__)


async def get_by_content_id(db: AsyncSession, *, content_id: UUID) -> ArticleLaymanSummary | None:
    """Get the stored summary for a shared content row."""
    result = await db.execute(select(ArticleLaymanSummary).where(ArticleLaymanSummary.content_id == content_id))
    return result.scalars().first()


async def upsert(
    db: AsyncSession,
    *,
    content_id: UUID,
    headline: str,
    what_happened: list[str],
    key_impact: str,
    model_identifier: str,
) -> ArticleLaymanSummary:
    """Create or replace the summary for a content row."""
    now = datetime.now(timezone.utc)
    existing = await get_by_content_id(db, content_id=content_id)
    if existing:
        existing.headline = headline
        existing.what_happened = what_happened
        existing.key_impact = key_impact
        existing.model_identifier = model_identifier
        existing.generated_at = now
        existing.updated_at = now
        row = existing
    else:
        row = ArticleLaymanSummary(
            content_id=content_id,
            headline=headline,
            what_happened=what_happened,
            key_impact=key_impact,
            model_identifier=model_identifier,
            generated_at=now,
        )
        db.add(row)

    await db.flush()
    await db.refresh(row)
    logger.info("Upserted layman summary", content_id=str(content_id))
    return row
