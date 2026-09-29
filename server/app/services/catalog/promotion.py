"""Promote a catalog feed into a user's feed library on explicit subscribe.

The catalog is a discovery store: nothing enters the global ``feeds`` table until a user
subscribes. This module resolves the URL to actually subscribe to (native feed URL, or the
backend-served synthetic Atom URL) and delegates to the existing ``add_feed`` pipeline so
fetching, parsing, ingestion, scheduling and Meilisearch all behave identically.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

import structlog

from app.core.custom_exceptions import NotFoundError, ValidationError
from app.crud.catalog import feeds as catalog_feed_crud
from app.crud.feed import core as feed_crud
from app.models.catalog import CatalogFeed
from app.models.enums import CatalogFeedType, VerificationStatus
from app.services.catalog.synthetic import build_synthetic_feed_url
from app.services.feeds.service import add_feed

logger = structlog.get_logger(__name__)

SessionFactory = Callable[[], Any]


def resolve_subscribable_url(feed: CatalogFeed) -> str:
    """The URL to subscribe to: the native feed URL, or the generated Atom endpoint."""
    if feed.feed_type is CatalogFeedType.SYNTHETIC_HTML:
        return build_synthetic_feed_url(feed.id)
    return str(feed.feed_url)


async def subscribe_to_catalog_feed(
    session_factory: SessionFactory,
    *,
    user_id: UUID,
    catalog_feed_id: UUID,
    folder_id: UUID,
) -> tuple[Any, bool]:
    """Subscribe a user to a catalog feed, promoting it into the global ``feeds`` table.

    Returns the created subscription and whether it was newly created (mirrors ``add_feed``).
    """
    async with session_factory() as db:
        catalog_feed = await catalog_feed_crud.get_catalog_feed_by_id(db, feed_id=catalog_feed_id)
        if not catalog_feed:
            raise NotFoundError(message="Catalog feed not found")
        if catalog_feed.verification_status is VerificationStatus.REJECTED_AGGREGATOR:
            raise ValidationError(message="Rejected aggregator feeds cannot be subscribed to")
        entity_id = catalog_feed.entity_id
        target_url = resolve_subscribable_url(catalog_feed)

    subscription, created = await add_feed(session_factory, user_id=user_id, url=target_url, folder_id=folder_id)

    # Stamp provenance so the reader can badge the promoted feed as a primary source.
    async with session_factory() as db:
        global_feed = await feed_crud.get_feed_by_id(db, feed_id=subscription.feed_id)
        if global_feed is not None and global_feed.primary_entity_id is None:
            global_feed.primary_entity_id = entity_id
            await db.flush()

    logger.info(
        "Subscribed to catalog feed",
        catalog_feed_id=str(catalog_feed_id),
        feed_id=str(subscription.feed_id),
        created=created,
    )
    return subscription, created
