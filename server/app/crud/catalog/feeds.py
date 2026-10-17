"""CRUD operations for catalog feeds."""

from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogFeed
from app.models.enums import VerificationStatus
from app.typing.catalog import CatalogFeedCreate, GatekeeperResult
from app.utils.urls import normalize_feed_url

logger = structlog.get_logger(__name__)


def url_host_variants(url: str) -> list[str]:
    """Return ``url`` plus its ``www.``/apex host variant.

    ``normalize_feed_url`` does not treat ``www.audi.com`` and ``audi.com`` as the same feed,
    so without this a feed discovered on the apex host and the same feed seeded on ``www.``
    (or vice-versa) would be catalogued twice. The variants let the dedup lookup catch both.
    """
    variants = {url}
    parsed = urlparse(url)
    host = parsed.netloc
    if parsed.scheme not in ("http", "https") or not host:
        return list(variants)
    if host.startswith("www."):
        variants.add(urlunparse(parsed._replace(netloc=host[4:])))
    else:
        variants.add(urlunparse(parsed._replace(netloc=f"www.{host}")))
    return list(variants)


async def get_catalog_feed_by_url(db: AsyncSession, *, url: str) -> CatalogFeed | None:
    """Get a catalog feed by URL, treating ``www.``/apex host variants as the same feed."""
    variants = url_host_variants(normalize_feed_url(url))
    result = await db.execute(select(CatalogFeed).where(CatalogFeed.feed_url.in_(variants)))
    return result.scalars().first()


async def get_catalog_feed_by_id(db: AsyncSession, *, feed_id: UUID) -> CatalogFeed | None:
    """Get a catalog feed by primary key."""
    result = await db.execute(select(CatalogFeed).where(CatalogFeed.id == feed_id))
    return result.scalars().first()


async def get_catalog_feeds_due(db: AsyncSession, *, limit: int = 100) -> list[CatalogFeed]:
    """List catalog feeds due for verification, oldest due first.

    Rejected aggregators are terminal and skipped; quarantined feeds are retried only once
    their (long) ``next_poll_at`` elapses.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(CatalogFeed)
        .where(CatalogFeed.next_poll_at <= now)
        .where(CatalogFeed.verification_status != VerificationStatus.REJECTED_AGGREGATOR)
        .order_by(CatalogFeed.next_poll_at.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_catalog_feeds(
    db: AsyncSession, *, entity_id: UUID | None = None, limit: int = 100, offset: int = 0
) -> list[CatalogFeed]:
    """List catalog feeds, optionally filtered by entity."""
    stmt = select(CatalogFeed).order_by(CatalogFeed.created_at.desc()).limit(limit).offset(offset)
    if entity_id is not None:
        stmt = stmt.where(CatalogFeed.entity_id == entity_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_catalog_feed(db: AsyncSession, *, data: CatalogFeedCreate) -> CatalogFeed:
    """Create a candidate feed, returning the existing row for a URL already catalogued."""
    normalized = normalize_feed_url(data.feed_url)
    existing = await get_catalog_feed_by_url(db, url=normalized)
    if existing:
        return existing

    feed = CatalogFeed(entity_id=data.entity_id, feed_url=normalized, feed_type=data.feed_type)
    db.add(feed)
    await db.flush()
    await db.refresh(feed)
    logger.info("Created catalog feed", feed_id=str(feed.id), url=normalized)
    return feed


async def apply_verification(db: AsyncSession, *, feed: CatalogFeed, result: GatekeeperResult) -> CatalogFeed:
    """Persist a gatekeeper verdict onto a catalog feed."""
    now = datetime.now(timezone.utc)
    feed.verification_status = result.status
    feed.rejection_reason = result.reason
    feed.outbound_third_party_ratio = result.outbound_third_party_ratio
    feed.last_polled_at = now
    feed.last_updated_at = now
    await db.flush()
    await db.refresh(feed)
    logger.info("Applied verification", feed_id=str(feed.id), status=result.status.value)
    return feed
