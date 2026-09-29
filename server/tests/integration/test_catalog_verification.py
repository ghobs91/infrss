"""Integration tests for catalog verification (gatekeeper applied via the service)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.crud.catalog import entities, feeds
from app.models.enums import CatalogFeedType, EntityType, VerificationStatus
from app.services.catalog.verification import verify_catalog_feed
from app.typing.catalog import CatalogFeedCreate, PrimaryEntityCreate


class _SessionFactory:
    """Yields the test session on each acquire (stands in for worker_db_factory)."""

    def __init__(self, session) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _rss(links: list[str]) -> str:
    items = "".join(f"<item><title>t</title><link>{link}</link></item>" for link in links)
    return f"<rss version='2.0'><channel><title>FDA News</title>{items}</channel></rss>"


def _fetch_result(content: str, error: str | None = None) -> dict:
    return {
        "content": content,
        "headers": {"etag": "abc"},
        "status_code": 200 if not error else 500,
        "not_modified": False,
        "error": error,
        "final_url": "https://www.fda.gov/rss.xml",
        "permanent_redirect": False,
    }


async def _catalog_feed(db_session, *, feed_url: str = "https://www.fda.gov/rss.xml"):
    entity = await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(name="FDA", entity_type=EntityType.GOV_FEDERAL, canonical_domain="fda.gov"),
    )
    return await feeds.create_catalog_feed(
        db_session,
        data=CatalogFeedCreate(entity_id=entity.id, feed_url=feed_url, feed_type=CatalogFeedType.NATIVE_RSS),
    )


@pytest.mark.asyncio
async def test_verify_marks_on_domain_feed_verified(db_session):
    feed = await _catalog_feed(db_session)
    content = _rss(["https://www.fda.gov/news/1", "https://www.fda.gov/news/2"])

    with patch(
        "app.services.catalog.verification.fetching.fetch_feed_content",
        new=AsyncMock(return_value=_fetch_result(content)),
    ):
        await verify_catalog_feed(_SessionFactory(db_session), feed.id)

    await db_session.refresh(feed)
    assert feed.verification_status is VerificationStatus.VERIFIED_PRIMARY
    assert feed.failure_count == 0
    assert feed.etag_header == "abc"
    assert feed.last_polled_at is not None


@pytest.mark.asyncio
async def test_verify_rejects_aggregator(db_session):
    feed = await _catalog_feed(db_session)
    links = ["https://www.fda.gov/1"] + [f"https://reuters.com/{i}" for i in range(5)]

    with patch(
        "app.services.catalog.verification.fetching.fetch_feed_content",
        new=AsyncMock(return_value=_fetch_result(_rss(links))),
    ):
        await verify_catalog_feed(_SessionFactory(db_session), feed.id)

    await db_session.refresh(feed)
    assert feed.verification_status is VerificationStatus.REJECTED_AGGREGATOR
    assert feed.rejection_reason is not None


@pytest.mark.asyncio
async def test_verify_records_failure_and_backs_off(db_session):
    feed = await _catalog_feed(db_session)

    with patch(
        "app.services.catalog.verification.fetching.fetch_feed_content",
        new=AsyncMock(return_value=_fetch_result("", error="HTTP 500")),
    ):
        await verify_catalog_feed(_SessionFactory(db_session), feed.id)

    await db_session.refresh(feed)
    assert feed.failure_count == 1
    assert feed.verification_status is VerificationStatus.PENDING
    assert feed.rejection_reason is None
