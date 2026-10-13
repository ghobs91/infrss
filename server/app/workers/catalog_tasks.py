"""Catalog-related Taskiq tasks."""

from typing import Any
from uuid import UUID

from app.core.taskiq_app import broker
from app.workers.catalog.discover import discover_catalog_feeds_worker
from app.workers.catalog.sync import (
    sync_federal_register_agencies,
    sync_sec_ciks,
    sync_wikidata_entities,
)
from app.workers.catalog.verify import (
    schedule_catalog_verifications,
    verify_single_catalog_feed,
)
from app.workers.common import ensure_uuid


@broker.task(task_name="catalog_tasks.verify_single_feed")
async def verify_catalog_feed_task(catalog_feed_id: UUID | str) -> None:
    """Verify a single catalog feed (wrapper)."""
    await verify_single_catalog_feed(ensure_uuid(catalog_feed_id))


@broker.task(
    task_name="catalog_tasks.schedule_verifications",
    schedule=[{"cron": "0 */2 * * *"}],
)
async def schedule_catalog_verifications_task() -> None:
    """Cron: dispatch due catalog verifications every two hours."""
    await schedule_catalog_verifications()


@broker.task(
    task_name="catalog_tasks.sync_sec_ciks",
    schedule=[{"cron": "0 5 * * *"}],
)
async def sync_sec_ciks_task() -> dict[str, Any]:
    """Cron: refresh SEC CIK mappings daily."""
    return await sync_sec_ciks()


@broker.task(
    task_name="catalog_tasks.sync_federal_register",
    schedule=[{"cron": "0 6 * * 1"}],
)
async def sync_federal_register_task() -> dict[str, Any]:
    """Cron: refresh Federal Register agencies weekly."""
    return await sync_federal_register_agencies()


@broker.task(
    task_name="catalog_tasks.sync_wikidata",
    schedule=[{"cron": "0 7 * * 1"}],
)
async def sync_wikidata_task() -> dict[str, Any]:
    """Cron: refresh Wikidata entities weekly."""
    return await sync_wikidata_entities()


@broker.task(
    task_name="catalog_tasks.discover_feeds",
    schedule=[{"cron": "0 8 * * *"}],
)
async def discover_catalog_feeds_task() -> dict[str, Any]:
    """Cron: discover candidate feeds for synced entities that have none yet.

    Runs after the connector syncs (SEC 05:00 daily, Federal Register and Wikidata Monday 06:00/07:00)
    so newly ingested entities get a discovery pass on the same day. The verification scheduler then
    picks the new candidates up on its two-hourly sweep.
    """
    return await discover_catalog_feeds_worker()
