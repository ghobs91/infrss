"""Autodiscovery: find RSS/Atom feeds advertised by, or hosted on, a primary domain.

For a target domain this inspects newsroom-style pages for ``<link rel="alternate">`` feed
declarations, then falls back to probing well-known feed endpoints. All outbound requests go
through the SSRF-safe helpers in :mod:`app.services.feeds.fetching`.
"""

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup, Tag

from app.core.constants import CATALOG_AUTODISCOVERY_PATHS, CATALOG_PROBE_PATHS
from app.models.enums import CatalogFeedType
from app.services.feeds import fetching, parsing
from app.utils.urls import normalize_feed_url

logger = structlog.get_logger(__name__)

FEED_LINK_TYPES: dict[str, CatalogFeedType] = {
    "application/rss+xml": CatalogFeedType.NATIVE_RSS,
    "application/atom+xml": CatalogFeedType.NATIVE_ATOM,
}

_RSS_MARKER = re.compile(r"<\s*(rss|rdf:RDF)\b", re.IGNORECASE)
_ATOM_MARKER = re.compile(r"<\s*feed\b", re.IGNORECASE)
_ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"


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
    if not content:
        return None
    head = content[:4096]
    if _ATOM_NAMESPACE in head:
        return CatalogFeedType.NATIVE_ATOM
    if _RSS_MARKER.search(head):
        return CatalogFeedType.NATIVE_RSS
    if _ATOM_MARKER.search(head):
        return CatalogFeedType.NATIVE_ATOM
    return None


def extract_feed_links(html: str, base_url: str) -> list[DiscoveredFeed]:
    """Extract RSS/Atom ``<link rel="alternate">`` declarations from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    discovered: list[DiscoveredFeed] = []
    for tag in soup.find_all("link"):
        if not isinstance(tag, Tag):
            continue
        rel_value: Any = tag.get("rel") or []
        rel_list: list[str] = (
            [rel_value] if isinstance(rel_value, str) else [v for v in rel_value if isinstance(v, str)]
        )
        if "alternate" not in [value.lower() for value in rel_list]:
            continue
        feed_type = FEED_LINK_TYPES.get(str(tag.get("type", "")).lower().strip())
        href = tag.get("href")
        if not feed_type or not isinstance(href, str) or not href:
            continue
        title = tag.get("title")
        discovered.append(
            DiscoveredFeed(
                url=urljoin(base_url, href),
                feed_type=feed_type,
                title=title if isinstance(title, str) else None,
                source="link-tag",
            )
        )
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

    unique = dedupe_feeds(discovered)
    logger.info("Autodiscovery complete", target=base_url, found=len(unique))
    return DiscoveryResult(target_url=base_url, feeds=unique)
