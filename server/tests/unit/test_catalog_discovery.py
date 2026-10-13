"""Unit tests for catalog discovery orchestration (database and network mocked)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.enums import CatalogFeedType
from app.services.catalog import discovery
from app.services.catalog.autodiscovery import DiscoveredFeed, DiscoveryResult


@pytest.mark.asyncio
@pytest.mark.unit
async def test_discover_entity_feeds_persists_candidates(monkeypatch):
    entity_id = uuid4()
    entity = SimpleNamespace(id=entity_id, canonical_domain="example.com")
    result = DiscoveryResult(
        target_url="https://example.com",
        feeds=[
            DiscoveredFeed(url="https://example.com/press/rss.xml", feed_type=CatalogFeedType.NATIVE_RSS),
            DiscoveredFeed(url="https://example.com/atom.xml", feed_type=CatalogFeedType.NATIVE_ATOM),
        ],
    )
    monkeypatch.setattr(discovery, "discover_feeds", AsyncMock(return_value=result))
    create = AsyncMock()
    monkeypatch.setattr(discovery.feed_crud, "create_catalog_feed", create)

    created = await discovery.discover_entity_feeds(AsyncMock(), entity)

    assert created == 2
    assert create.await_count == 2
    first = create.await_args_list[0].kwargs["data"]
    assert first.entity_id == entity_id
    assert first.feed_url == "https://example.com/press/rss.xml"
    assert first.feed_type is CatalogFeedType.NATIVE_RSS


@pytest.mark.asyncio
@pytest.mark.unit
async def test_discover_catalog_feeds_continues_after_one_domain_fails(monkeypatch):
    entities = [
        SimpleNamespace(id="a", canonical_domain="a.example"),
        SimpleNamespace(id="b", canonical_domain="b.example"),
    ]
    monkeypatch.setattr(
        discovery.entity_crud,
        "get_entities_without_catalog_feeds",
        AsyncMock(return_value=entities),
    )

    async def fake_discover(_db, entity):
        if entity.canonical_domain == "a.example":
            raise RuntimeError("boom")
        return 1

    monkeypatch.setattr(discovery, "discover_entity_feeds", fake_discover)

    created = await discovery.discover_catalog_feeds(AsyncMock())

    assert created == 1
