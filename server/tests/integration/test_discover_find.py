"""Tests for the feed finder endpoint (network calls patched, database real)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.feeds.discovery import (
    DiscoveryStepKey,
    DiscoveryStepResult,
    DiscoveryStepStatus,
    FeedCandidate,
    FeedDiscoveryReport,
)
from app.services.feeds.feed_detection import FeedFormat

RSS_DOCUMENT = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Example News</title>
  <link>https://example.com</link>
  <description>News from example.com</description>
  <item><title>First</title><link>https://example.com/one</link></item>
</channel></rss>"""


def _report(**overrides) -> FeedDiscoveryReport:
    """Build a discovery report shaped like a real run."""
    defaults = {
        "input_url": "https://example.com/blog",
        "base_url": "https://example.com/blog",
        "is_direct_feed": False,
        "candidates": [
            FeedCandidate(
                url="https://example.com/feed.xml",
                content=RSS_DOCUMENT,
                format=FeedFormat.RSS,
                title="Example News",
            )
        ],
        "steps": [
            DiscoveryStepResult(key=DiscoveryStepKey.DIRECT, label="Checking feed", status=DiscoveryStepStatus.OK),
            DiscoveryStepResult(
                key=DiscoveryStepKey.AUTODISCOVERY,
                label="Checking RSS autodiscovery",
                status=DiscoveryStepStatus.OK,
                found=1,
            ),
            DiscoveryStepResult(
                key=DiscoveryStepKey.SITE_LINKS,
                label="Searching all website links",
                status=DiscoveryStepStatus.SKIPPED,
            ),
        ],
    }
    defaults.update(overrides)
    return FeedDiscoveryReport(**defaults)


class TestFindFeeds:
    """Test the /discover/find endpoint."""

    @pytest.mark.asyncio
    async def test_find_feeds_returns_discovered_feed_preview(self, async_client: AsyncClient):
        report = _report()
        with patch(
            "app.services.feeds.discovery.discover_feeds_for_url",
            new=AsyncMock(return_value=report),
        ):
            response = await async_client.get("/api/discover/find", params={"url": "https://example.com/blog"})

        assert response.status_code == 200
        data = response.json()

        assert data["input_url"] == "https://example.com/blog"
        assert data["is_direct_feed"] is False
        assert len(data["feeds"]) == 1

        feed = data["feeds"][0]
        assert feed["title"] == "Example News"
        assert feed["url"] == "https://example.com/feed.xml"
        assert feed["description"] == "News from example.com"
        # Discovery responses carry no articles; the preview card does not render them.
        assert feed["articles"] == []
        assert feed["is_subscribed"] is False

        assert [step["key"] for step in data["steps"]] == ["direct", "autodiscovery", "site_links"]
        assert data["steps"][1]["found"] == 1
        assert data["steps"][2]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_find_feeds_returns_empty_when_nothing_is_discovered(self, async_client: AsyncClient):
        report = _report(candidates=[], is_direct_feed=False)
        with patch(
            "app.services.feeds.discovery.discover_feeds_for_url",
            new=AsyncMock(return_value=report),
        ):
            response = await async_client.get("/api/discover/find", params={"url": "https://example.com/blog"})

        assert response.status_code == 200
        assert response.json()["feeds"] == []

    @pytest.mark.asyncio
    async def test_find_feeds_adds_scheme_to_bare_domains(self, async_client: AsyncClient):
        report = _report(input_url="https://example.com", base_url="https://example.com")
        finder = AsyncMock(return_value=report)
        with patch("app.services.feeds.discovery.discover_feeds_for_url", new=finder):
            response = await async_client.get("/api/discover/find", params={"url": "example.com"})

        assert response.status_code == 200
        finder.assert_awaited_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_find_feeds_missing_url(self, async_client: AsyncClient):
        response = await async_client.get("/api/discover/find")

        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:6379",
            "http://localhost:8008/",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
        ],
    )
    async def test_find_feeds_blocks_internal_urls(self, async_client: AsyncClient, url: str):
        """SSRF: internal/metadata targets are rejected before any request is made."""
        finder = AsyncMock(return_value=_report())
        with patch("app.services.feeds.discovery.discover_feeds_for_url", new=finder):
            response = await async_client.get("/api/discover/find", params={"url": url})

        assert response.status_code == 400
        finder.assert_not_awaited()
