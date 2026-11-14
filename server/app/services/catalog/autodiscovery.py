"""Autodiscovery: find RSS/Atom feeds advertised by, or hosted on, a primary domain.

For a target domain this inspects newsroom-style pages for ``<link rel="alternate">`` feed
declarations, then falls back to probing well-known feed endpoints. All outbound requests go
through the SSRF-safe helpers in :mod:`app.services.feeds.fetching`.

Feed document classification and link-tag parsing live in :mod:`app.services.feeds.feed_detection`;
this module only maps them onto catalog-specific vocabularies.
"""

from dataclasses import dataclass, field
from urllib.parse import urlparse

import structlog

from app.core.constants import (
    CATALOG_AUTODISCOVERY_PATHS,
    CATALOG_DISCOVERY_SUBDOMAINS,
    CATALOG_PROBE_PATHS,
    CATALOG_SUBDOMAIN_PROBE_PATHS,
)
from app.models.enums import CatalogFeedType
from app.services.feeds import fetching, parsing
from app.services.feeds.feed_detection import (
    FeedFormat,
    detect_feed_format,
    extract_feed_link_tags,
)
from app.utils.urls import normalize_feed_url

logger = structlog.get_logger(__name__)

FEED_FORMAT_TYPES: dict[FeedFormat, CatalogFeedType] = {
    FeedFormat.RSS: CatalogFeedType.NATIVE_RSS,
    FeedFormat.ATOM: CatalogFeedType.NATIVE_ATOM,
}


@dataclass(frozen=True)
class DiscoveredFeed:
    """A feed candidate found by autodiscovery."""

    url: str
    feed_type: CatalogFeedType
    title: str | None = None
    source: str = "link-tag"  # "link-tag" or "probe"


@dataclass(frozen=True)
class DiscoveryResult:
    """Outcome of an autodiscovery run against one target domain or page."""

    target_url: str
    feeds: list[DiscoveredFeed] = field(default_factory=list)
    error: str | None = None


def detect_feed_type(content: str) -> CatalogFeedType | None:
    """Classify raw XML as RSS/RDF or Atom; ``None`` when it is neither."""
    feed_format = detect_feed_format(content)
    return FEED_FORMAT_TYPES.get(feed_format) if feed_format else None


def extract_feed_links(html: str, base_url: str) -> list[DiscoveredFeed]:
    """Extract RSS/Atom ``<link rel="alternate">`` declarations from an HTML page."""
    discovered: list[DiscoveredFeed] = []
    for link in extract_feed_link_tags(html, base_url):
        feed_type = FEED_FORMAT_TYPES.get(link.format)
        if feed_type is None:
            continue
        discovered.append(DiscoveredFeed(url=link.url, feed_type=feed_type, title=link.title, source="link-tag"))
    return discovered


def build_base_url(target: str) -> str:
    """Normalize a bare domain or URL to its scheme + host origin."""
    candidate = target.strip()
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return candidate
    return f"{parsed.scheme}://{parsed.netloc}"


def dedupe_feeds(feeds: list[DiscoveredFeed]) -> list[DiscoveredFeed]:
    """Drop duplicate candidates by normalized feed URL, preserving discovery order."""
    seen: set[str] = set()
    unique: list[DiscoveredFeed] = []
    for feed in feeds:
        key = normalize_feed_url(feed.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(feed)
    return unique


async def probe_endpoint(url: str) -> DiscoveredFeed | None:
    """Return a feed candidate when ``url`` actually serves an RSS/Atom document."""
    result = await fetching.fetch_feed_content(url)
    if result["error"] or not result["content"]:
        return None
    feed_type = detect_feed_type(result["content"])
    if feed_type is None:
        return None
    try:
        title = parsing.parse_feed_content(result["content"], url).title
    except Exception as exc:  # noqa: BLE001 - a malformed feed is simply not a usable candidate
        logger.debug("Probed endpoint parsed as a feed but metadata failed", url=url, error=str(exc))
        title = None
    return DiscoveredFeed(url=url, feed_type=feed_type, title=title, source="probe")


async def discover_feeds(target: str) -> DiscoveryResult:
    """Find candidate feeds advertised by a domain's HTML, or served at well-known paths."""
    base_url = build_base_url(target)
    pages = [base_url, *[f"{base_url}{path}" for path in CATALOG_AUTODISCOVERY_PATHS]]

    discovered: list[DiscoveredFeed] = []
    for page in pages:
        html = await fetching.fetch_page_html(page)
        if not html:
            continue
        discovered.extend(extract_feed_links(html, page))
        if discovered:
            break

    if not discovered:
        # Probing is a fallback that only needs one feed, so stop at the first hit rather than
        # sweeping every well-known path.
        candidates = [base_url, *[f"{base_url}{path}" for path in CATALOG_PROBE_PATHS]]
        for candidate in candidates:
            probed = await probe_endpoint(candidate)
            if probed:
                discovered.append(probed)
                break

    if not discovered:
        # Many organisations advertise their newsroom on a subdomain (newsroom.acme.com,
        # press.acme.com) rather than the canonical marketing site. Scan those pages for feed
        # declarations, then probe the usual endpoints on each subdomain.
        host = urlparse(base_url).netloc
        for subdomain in CATALOG_DISCOVERY_SUBDOMAINS:
            sub_base = f"https://{subdomain}.{host}"
            html = await fetching.fetch_page_html(sub_base)
            if html:
                discovered.extend(extract_feed_links(html, sub_base))
            if discovered:
                break
            for path in CATALOG_SUBDOMAIN_PROBE_PATHS:
                probed = await probe_endpoint(f"{sub_base}{path}")
                if probed:
                    discovered.append(probed)
                    break
            if discovered:
                break

    unique = dedupe_feeds(discovered)
    logger.info("Autodiscovery complete", target=base_url, found=len(unique))
    return DiscoveryResult(target_url=base_url, feeds=unique)
