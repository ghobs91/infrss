"""CRUD operations for primary entities."""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogFeed, PrimaryEntity
from app.models.enums import FeedCategory, VerificationStatus
from app.typing.catalog import PrimaryEntityCreate

logger = structlog.get_logger(__name__)


def normalize_domain(domain: str) -> str:
    """Lower-case a domain and strip a trailing dot so it deduplicates consistently."""
    return (domain or "").strip().lower().rstrip(".")


async def get_entity_by_domain(db: AsyncSession, *, canonical_domain: str) -> PrimaryEntity | None:
    """Get an entity by its canonical domain (normalized before comparison)."""
    result = await db.execute(
        select(PrimaryEntity).where(PrimaryEntity.canonical_domain == normalize_domain(canonical_domain))
    )
    return result.scalars().first()


async def get_entity_by_id(db: AsyncSession, *, entity_id: UUID) -> PrimaryEntity | None:
    """Get an entity by primary key."""
    result = await db.execute(select(PrimaryEntity).where(PrimaryEntity.id == entity_id))
    return result.scalars().first()


async def get_entities_missing_cik(db: AsyncSession, *, limit: int = 5000) -> list[PrimaryEntity]:
    """List entities that have not yet been matched to an SEC CIK."""
    result = await db.execute(
        select(PrimaryEntity).where(PrimaryEntity.cik.is_(None)).order_by(PrimaryEntity.created_at.asc()).limit(limit)
    )
    return list(result.scalars().all())


async def list_entities(db: AsyncSession, *, limit: int = 100, offset: int = 0) -> list[PrimaryEntity]:
    """List entities for catalog browsing, newest first."""
    result = await db.execute(select(PrimaryEntity).order_by(PrimaryEntity.name.asc()).limit(limit).offset(offset))
    return list(result.scalars().all())


async def list_sources_with_verified_feeds(
    db: AsyncSession,
    *,
    category: FeedCategory | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[tuple[PrimaryEntity, list[CatalogFeed]]]:
    """List browsable primary sources: entities that have at least one verified feed.

    Returns ``(entity, verified_feeds)`` pairs ordered by entity name. Entities lacking a
    verified feed are omitted so the browse view only ever shows usable sources. Feeds are
    loaded in a single follow-up query to avoid an N+1 per entity.
    """
    stmt = (
        select(PrimaryEntity)
        .where(
            exists().where(
                and_(
                    CatalogFeed.entity_id == PrimaryEntity.id,
                    CatalogFeed.verification_status == VerificationStatus.VERIFIED_PRIMARY,
                )
            )
        )
        .order_by(PrimaryEntity.name.asc())
        .limit(limit)
        .offset(offset)
    )
    if category is not None:
        stmt = stmt.where(PrimaryEntity.category == category)

    entities = list((await db.execute(stmt)).scalars().all())
    if not entities:
        return []

    entity_ids = [entity.id for entity in entities]
    feed_result = await db.execute(
        select(CatalogFeed)
        .where(
            CatalogFeed.entity_id.in_(entity_ids),
            CatalogFeed.verification_status == VerificationStatus.VERIFIED_PRIMARY,
        )
        .order_by(CatalogFeed.created_at.asc())
    )
    feeds_by_entity: dict[Any, list[CatalogFeed]] = {entity_id: [] for entity_id in entity_ids}
    for feed in feed_result.scalars().all():
        feeds_by_entity[feed.entity_id].append(feed)

    return [(entity, feeds_by_entity[entity.id]) for entity in entities]


async def get_entities_without_catalog_feeds(
    db: AsyncSession, *, limit: int = 1000, offset: int = 0
) -> list[PrimaryEntity]:
    """List entities that have no candidate feeds yet, oldest first.

    Discovery targets these so each entity is scanned once; entities that yielded feeds drop out
    of this set, while feedless ones are retried on later runs (autodiscovery has no negative
    cache, so a domain that publishes no feed is simply re-probed).
    """
    stmt = (
        select(PrimaryEntity)
        .where(~exists().where(CatalogFeed.entity_id == PrimaryEntity.id))
        .order_by(PrimaryEntity.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_entity(db: AsyncSession, *, data: PrimaryEntityCreate) -> PrimaryEntity:
    """Create an entity, returning the existing row when the domain is already catalogued.

    When the domain already exists but has no category and the incoming seed supplies one, the
    category is backfilled so re-running a connector (now or after editing its seed list) can
    classify entities that were first ingested without one.
    """
    domain = normalize_domain(data.canonical_domain)
    existing = await get_entity_by_domain(db, canonical_domain=domain)
    if existing:
        changed = False
        if existing.category is None and data.category is not None:
            existing.category = data.category
            changed = True
        if not existing.feed_hosts and data.feed_hosts:
            # Column attributes trip mypy's assignment check here, as with `category`.
            existing.feed_hosts = list(data.feed_hosts)  # type: ignore[assignment]
            changed = True
        if changed:
            await db.flush()
            await db.refresh(existing)
            logger.info("Backfilled entity metadata", entity_id=str(existing.id), domain=domain)
        return existing

    entity = PrimaryEntity(
        name=data.name,
        entity_type=data.entity_type,
        canonical_domain=domain,
        cik=data.cik,
        jurisdiction=data.jurisdiction,
        category=data.category,
        feed_hosts=list(data.feed_hosts) or None,
    )
    db.add(entity)
    await db.flush()
    await db.refresh(entity)
    logger.info("Created primary entity", entity_id=str(entity.id), domain=domain)
    return entity
