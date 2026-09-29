"""Integration tests for autodiscovery (network mocked) feeding catalog persistence."""

from unittest.mock import AsyncMock, patch

import pytest

from app.crud.catalog import entities, feeds
from app.models.enums import CatalogFeedType, EntityType
from app.services.catalog.autodiscovery import discover_feeds
from app.typing.catalog import CatalogFeedCreate, PrimaryEntityCreate

_FETCHING = "app.services.catalog.autodiscovery.fetching"


async def _make_entity(db_session, domain: str = "example.com"):
    return await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(
            name="Example Corp",
            entity_type=EntityType.CORP_PRIVATE,
            canonical_domain=domain,
        ),
    )


@pytest.mark.asyncio
async def test_discover_feeds_from_link_tags_then_persist(db_session):
    html = (
        "<html><head>"
        '<link rel="alternate" type="application/rss+xml" title="Press" href="/press/rss.xml">'
        "</head></html>"
    )
    entity = await _make_entity(db_session)

    with patch(f"{_FETCHING}.fetch_page_html", new=AsyncMock(return_value=html)):
        result = await discover_feeds("example.com")

    assert result.target_url == "https://example.com"
    assert [feed.url for feed in result.feeds] == ["https://example.com/press/rss.xml"]
    assert result.feeds[0].feed_type is CatalogFeedType.NATIVE_RSS

    stored = await feeds.create_catalog_feed(
        db_session,
        data=CatalogFeedCreate(
            entity_id=entity.id,
            feed_url=result.feeds[0].url,
            feed_type=result.feeds[0].feed_type,
        ),
    )
    assert stored.feed_url == "https://example.com/press/rss.xml"


@pytest.mark.asyncio
async def test_discover_feeds_probes_when_no_links_advertised(db_session):
    rss = (
        '<rss version="2.0"><channel><title>Corp News</title>'
        "<item><title>A</title><link>https://example.com/a</link></item></channel></rss>"
    )
    fetch_result = {
        "content": rss,
        "headers": {},
        "status_code": 200,
        "not_modified": False,
        "error": None,
        "final_url": "https://example.com/feed",
        "permanent_redirect": False,
    }

    with (
        patch(f"{_FETCHING}.fetch_page_html", new=AsyncMock(return_value=None)),
        patch(f"{_FETCHING}.fetch_feed_content", new=AsyncMock(return_value=fetch_result)),
    ):
        result = await discover_feeds("https://example.com")

    assert len(result.feeds) == 1
    assert result.feeds[0].source == "probe"
    assert result.feeds[0].feed_type is CatalogFeedType.NATIVE_RSS
