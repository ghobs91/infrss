"""Integration test for the generated synthetic Atom endpoint."""

from unittest.mock import AsyncMock, patch

import feedparser
import pytest

from app.crud.catalog import entities, feeds
from app.models.enums import CatalogFeedType, EntityType
from app.typing.catalog import CatalogFeedCreate, PrimaryEntityCreate

_NEWSROOM_HTML = """
<html><body>
<article><h2><a href="/news/a">Alpha</a></h2></article>
<article><h2><a href="/news/b">Beta</a></h2></article>
</body></html>
"""


@pytest.mark.asyncio
async def test_synthetic_endpoint_serves_atom(db_session, async_client):
    entity = await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(
            name="Example Corp", entity_type=EntityType.CORP_PRIVATE, canonical_domain="example.com"
        ),
    )
    catalog_feed = await feeds.create_catalog_feed(
        db_session,
        data=CatalogFeedCreate(
            entity_id=entity.id,
            feed_url="https://example.com/newsroom",
            feed_type=CatalogFeedType.SYNTHETIC_HTML,
        ),
    )

    with patch(
        "app.services.catalog.synthetic.fetching.fetch_page_html",
        new=AsyncMock(return_value=_NEWSROOM_HTML),
    ):
        response = await async_client.get(f"/api/catalog/synthetic/{catalog_feed.id}.atom")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/atom+xml")
    parsed = feedparser.parse(response.text)
    assert parsed.feed.title == "Example Corp"
    assert [entry.link for entry in parsed.entries] == [
        "https://example.com/news/a",
        "https://example.com/news/b",
    ]


@pytest.mark.asyncio
async def test_synthetic_endpoint_404_for_unknown_feed(db_session, async_client):
    response = await async_client.get("/api/catalog/synthetic/11111111-1111-1111-1111-111111111111.atom")
    assert response.status_code == 404
