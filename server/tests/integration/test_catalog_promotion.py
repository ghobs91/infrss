"""Integration tests for catalog feed promotion (subscribe-to-promote)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.crud.catalog import entities, feeds
from app.models.enums import CatalogFeedType, EntityType
from app.models.feed import Feed, FeedSubscription
from app.services.catalog.promotion import subscribe_to_catalog_feed
from app.typing.catalog import CatalogFeedCreate, PrimaryEntityCreate


class _SessionFactory:
    def __init__(self, session) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _mock_parsed_feed():
    parsed = MagicMock()
    parsed.title = "FDA Press Releases"
    parsed.description = "Official FDA news"
    parsed.link = "https://www.fda.gov"
    parsed.language = "en"
    parsed.image_url = None
    parsed.content_type = None
    parsed.author = None
    parsed.tags = []
    parsed.tags_native = []
    parsed.last_updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    parsed.articles = []
    return parsed


@pytest.mark.asyncio
async def test_subscribe_promotes_feed_and_stamps_entity(db_session, test_user, test_folder):
    entity = await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(name="FDA", entity_type=EntityType.GOV_FEDERAL, canonical_domain="fda.gov"),
    )
    catalog_feed = await feeds.create_catalog_feed(
        db_session,
        data=CatalogFeedCreate(
            entity_id=entity.id,
            feed_url="https://www.fda.gov/rss.xml",
            feed_type=CatalogFeedType.NATIVE_RSS,
        ),
    )

    fetch_result = {
        "content": "<rss/>",
        "headers": {},
        "status_code": 200,
        "not_modified": False,
        "error": None,
        "final_url": "https://www.fda.gov/rss.xml",
        "permanent_redirect": False,
    }

    with (
        patch(
            "app.services.feeds.service.fetching.fetch_feed_content",
            new=AsyncMock(return_value=fetch_result),
        ),
        patch("app.services.feeds.service.parsing.parse_feed_content", return_value=_mock_parsed_feed()),
        patch("app.services.feeds.service.sync_feed", new=AsyncMock()),
        patch("app.services.feeds.service.get_domain_authority_score") as score,
        patch(
            "app.services.feeds.service.scheduling.calculate_optimal_interval",
            new=AsyncMock(return_value=60),
        ),
        patch("app.services.feeds.service.calculate_feed_content_hash", return_value="hash"),
    ):
        score.return_value.score = 0.0
        subscription, created = await subscribe_to_catalog_feed(
            _SessionFactory(db_session),
            user_id=test_user.id,
            catalog_feed_id=catalog_feed.id,
            folder_id=test_folder.id,
        )

    assert created is True

    global_feed = (await db_session.execute(select(Feed).where(Feed.id == subscription.feed_id))).scalars().first()
    assert global_feed is not None
    assert global_feed.primary_entity_id == entity.id

    sub = (
        (await db_session.execute(select(FeedSubscription).where(FeedSubscription.feed_id == subscription.feed_id)))
        .scalars()
        .first()
    )
    assert sub is not None
    assert sub.user_id == test_user.id
