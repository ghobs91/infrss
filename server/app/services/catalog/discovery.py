"""Turn synced primary entities into candidate catalog feeds.

The connectors (Federal Register, Wikidata) populate :class:`PrimaryEntity` rows but carry no feed
URLs. This service closes the loop: for each entity it runs autodiscovery against the entity's own
domain and persists what it finds as ``PENDING`` catalog feeds, which the verification worker then
polls and gatekeeps. Entities without any feeds are skipped by the caller (see
:func:`discover_catalog_feeds`), so a given entity is only scanned until it yields a candidate.
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.catalog import entities as entity_crud
from app.crud.catalog import feeds as feed_crud
from app.models.catalog import PrimaryEntity
from app.services.catalog.autodiscovery import discover_feeds
from app.typing.catalog import CatalogFeedCreate

logger = structlog.get_logger(__name__)


async def discover_entity_feeds(db: AsyncSession, entity: PrimaryEntity) -> int:
    """Run autodiscovery for one entity and persist its candidate feeds. Returns the count."""
    result = await discover_feeds(entity.canonical_domain)
    created = 0
    for candidate in result.feeds:
        await feed_crud.create_catalog_feed(
            db,
            data=CatalogFeedCreate(
                entity_id=entity.id,
                feed_url=candidate.url,
                feed_type=candidate.feed_type,
            ),
        )
        created += 1
    return created


async def discover_catalog_feeds(db: AsyncSession) -> int:
    """Discover and persist feeds for every entity that has none yet. Returns feeds created."""
    entities = await entity_crud.get_entities_without_catalog_feeds(db)
    created = 0
    for entity in entities:
        try:
            created += await discover_entity_feeds(db, entity)
        except Exception as exc:  # noqa: BLE001 - one bad domain must not abort the whole sweep
            logger.warning(
                "Catalog feed discovery failed",
                entity_id=str(entity.id),
                domain=entity.canonical_domain,
                error=str(exc),
            )
    logger.info("Catalog discovery complete", entities=len(entities), created=created)
    return created
