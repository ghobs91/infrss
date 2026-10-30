"""Unit tests for per-user catalog subscription flags (pure, no network or database)."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.enums import CatalogFeedType
from app.routers.catalog import _is_catalog_feed_subscribed
from app.services.catalog.synthetic import build_synthetic_feed_url
from app.utils.urls import normalize_feed_url


def _feed(url: str, feed_type: CatalogFeedType = CatalogFeedType.NATIVE_RSS):
    return SimpleNamespace(id=uuid4(), feed_url=url, feed_type=feed_type)


@pytest.mark.unit
def test_native_feed_matches_normalized_subscription_url():
    feed = _feed("https://Example.com/feed/")
    urls = {normalize_feed_url("https://example.com/feed/")}

    assert _is_catalog_feed_subscribed(feed, set(), urls)
    assert not _is_catalog_feed_subscribed(feed, set(), set())
    assert not _is_catalog_feed_subscribed(feed, set(), {normalize_feed_url("https://example.com/other")})


@pytest.mark.unit
def test_feed_matches_by_promoted_catalog_feed_id():
    feed = _feed("https://tsa.gov/rss.xml")

    # The promoted feed's stored URL can differ (redirect/www); the id match is authoritative.
    assert _is_catalog_feed_subscribed(feed, {feed.id}, set())
    assert not _is_catalog_feed_subscribed(feed, {uuid4()}, set())


@pytest.mark.unit
def test_native_feed_matches_www_variant_of_subscription_url():
    feed = _feed("https://tsa.gov/rss.xml")
    urls = {normalize_feed_url("https://www.tsa.gov/rss.xml")}

    assert _is_catalog_feed_subscribed(feed, set(), urls)


@pytest.mark.unit
def test_synthetic_feed_matches_the_promoted_atom_endpoint():
    feed = _feed("https://example.com/news", CatalogFeedType.SYNTHETIC_HTML)
    promoted_url = build_synthetic_feed_url(feed.id)

    assert _is_catalog_feed_subscribed(feed, set(), {normalize_feed_url(promoted_url)})
    # The raw newsroom page is not what gets subscribed to for a synthetic source.
    assert not _is_catalog_feed_subscribed(feed, set(), {normalize_feed_url(feed.feed_url)})
