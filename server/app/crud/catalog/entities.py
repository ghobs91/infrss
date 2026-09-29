"""CRUD operations for primary entities."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import PrimaryEntity
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


async def create_entity(db: AsyncSession, *, data: PrimaryEntityCreate) -> PrimaryEntity:
    """Create an entity, returning the existing row when the domain is already catalogued."""
    domain = normalize_domain(data.canonical_domain)
    existing = await get_entity_by_domain(db, canonical_domain=domain)
    if existing:
        return existing

    entity = PrimaryEntity(
        name=data.name,
        entity_type=data.entity_type,
        canonical_domain=domain,
        cik=data.cik,
        jurisdiction=data.jurisdiction,
    )
    db.add(entity)
    await db.flush()
    await db.refresh(entity)
    logger.info("Created primary entity", entity_id=str(entity.id), domain=domain)
    return entity
