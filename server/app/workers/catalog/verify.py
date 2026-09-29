"""Catalog verification worker operations."""

from uuid import UUID

import structlog

from app.core.constants import CATALOG_VERIFY_BATCH_SIZE
from app.crud.catalog.feeds import get_catalog_feeds_due
from app.services.catalog.verification import verify_catalog_feed
from app.workers.common import worker_db_factory

logger = structlog.get_logger(__name__)


async def verify_single_catalog_feed(catalog_feed_id: UUID) -> None:
    """Verify one catalog feed using the service layer."""
    await verify_catalog_feed(worker_db_factory, catalog_feed_id)


async def schedule_catalog_verifications() -> None:
    """Dispatch verification tasks for catalog feeds whose next poll is due."""
    async with worker_db_factory() as db:
        due = await get_catalog_feeds_due(db, limit=CATALOG_VERIFY_BATCH_SIZE)
        feed_ids = [feed.id for feed in due]

    if not feed_ids:
        logger.info("No catalog feeds due for verification")
        return

    logger.info("Dispatching catalog verifications", count=len(feed_ids))

    # Lazy import avoids a circular dependency at module load.
    from app.workers.catalog_tasks import verify_catalog_feed_task

    for feed_id in feed_ids:
        await verify_catalog_feed_task.kiq(feed_id)
