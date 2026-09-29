"""Unit tests for autodiscovery HTML/feed detection (pure logic, no network)."""

import pytest

from app.models.enums import CatalogFeedType
from app.services.catalog.autodiscovery import (
    DiscoveredFeed,
    build_base_url,
    dedupe_feeds,
    detect_feed_type,
    extract_feed_links,
)


@pytest.mark.unit
def test_extract_feed_links_reads_rss_and_atom_tags():
    html = """
    <html><head>
      <link rel="alternate" type="application/rss+xml" title="Press" href="/press/rss.xml">
      <link rel="alternate" type="application/atom+xml" href="https://example.com/atom.xml">
      <link rel="alternate" type="text/html" href="/index.html">
    </head></html>
    """
    feeds = extract_feed_links(html, "https://example.com/newsroom")

    assert [feed.url for feed in feeds] == [
        "https://example.com/press/rss.xml",
        "https://example.com/atom.xml",
    ]
    assert feeds[0].feed_type is CatalogFeedType.NATIVE_RSS
    assert feeds[0].title == "Press"
    assert feeds[0].source == "link-tag"
    assert feeds[1].feed_type is CatalogFeedType.NATIVE_ATOM


@pytest.mark.unit
def test_extract_feed_links_ignores_non_alternate_links():
    html = '<link rel="stylesheet" type="application/rss+xml" href="/style.xml">'
    assert extract_feed_links(html, "https://example.com") == []


@pytest.mark.unit
def test_build_base_url_from_bare_domain_or_url():
    assert build_base_url("fda.gov") == "https://fda.gov"
    assert build_base_url("https://fda.gov/newsroom?x=1") == "https://fda.gov"
    assert build_base_url("http://example.com/press") == "http://example.com"


@pytest.mark.unit
def test_detect_feed_type():
    assert detect_feed_type("<rss version='2.0'><channel></channel></rss>") is CatalogFeedType.NATIVE_RSS
    assert detect_feed_type("<feed xmlns='http://www.w3.org/2005/Atom'></feed>") is CatalogFeedType.NATIVE_ATOM
    assert detect_feed_type("<html><body>hi</body></html>") is None
    assert detect_feed_type("") is None


@pytest.mark.unit
def test_dedupe_feeds_keeps_first_occurrence():
    feeds = [
        DiscoveredFeed(url="https://example.com/rss.xml", feed_type=CatalogFeedType.NATIVE_RSS),
        DiscoveredFeed(url="https://example.com/rss.xml", feed_type=CatalogFeedType.NATIVE_RSS),
        DiscoveredFeed(url="https://example.com/atom.xml", feed_type=CatalogFeedType.NATIVE_ATOM),
    ]
    assert len(dedupe_feeds(feeds)) == 2
