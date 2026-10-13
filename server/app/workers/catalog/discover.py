"""Catalog discovery worker: expand synced entities into candidate catalog feeds."""

import structlog

from app.services.catalog.discovery import discover_catalog_feeds
from app.workers.common import worker_db_factory

logger = structlog.get_logger(__name__)


async def discover_catalog_feeds_worker() -> dict[str, int]:
    """Run autodiscovery for entities lacking feeds and return the number of feeds created."""
    async with worker_db_factory() as db:
        created = await discover_catalog_feeds(db)
    return {"created": created}
