"""Synthetic newsroom feeds: extract structured items from HTML and emit Atom 1.0.

The DOM parser is the default path (``bs4``, already a dependency); Playwright is an optional
fallback for JS-rendered newsrooms, gated by ``SYNTHETIC_USE_BROWSER`` and imported lazily so the
package is not required for the common case.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin
from uuid import UUID
from xml.sax.saxutils import escape, quoteattr

import structlog
from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from app.core import redis_cache
from app.core.config import get_settings
from app.core.constants import (
    CATALOG_CONNECTOR_TIMEOUT,
    CATALOG_SYNTHETIC_CACHE_TTL_SECONDS,
    CATALOG_SYNTHETIC_FEED_PATH,
    CATALOG_SYNTHETIC_MAX_ITEMS,
    CATALOG_SYNTHETIC_MIN_ITEMS,
)
from app.crud.catalog import entities as entity_crud
from app.crud.catalog import feeds as feed_crud
from app.models.enums import CatalogFeedType
from app.services.catalog.gatekeeper import domain_from_url, is_domain_aligned
from app.services.feeds import fetching

logger = structlog.get_logger(__name__)

SessionFactory = Callable[[], Any]

_HEADING_TAGS = ("h1", "h2", "h3", "h4")


@dataclass(frozen=True)
class NewsItem:
    """A single item extracted from a newsroom page."""

    title: str
    url: str
    published_at: datetime | None = None


def build_synthetic_feed_url(catalog_feed_id: UUID) -> str:
    """Absolute URL the backend serves a catalog feed's generated Atom from."""
    base = get_settings().SYNTHETIC_FEED_BASE_URL.rstrip("/")
    return f"{base}{CATALOG_SYNTHETIC_FEED_PATH.format(feed_id=catalog_feed_id)}"


def _heading_link(node: Tag) -> Tag | None:
    """Return the first anchor inside a heading, falling back to any anchor in the node."""
    for tag_name in _HEADING_TAGS:
        heading = node.find(tag_name)
        if isinstance(heading, Tag):
            anchor = heading.find("a")
            if isinstance(anchor, Tag):
                return anchor
    anchor = node.find("a")
    return anchor if isinstance(anchor, Tag) else None


def _parse_datetime(node: Tag) -> datetime | None:
    """Extract a timestamp from a ``<time>`` element, if present and parseable."""
    time_tag = node.find("time")
    if not isinstance(time_tag, Tag):
        return None
    raw = time_tag.get("datetime") or time_tag.get_text(strip=True)
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed: datetime = date_parser.parse(raw, fuzzy=True)
    except (ValueError, OverflowError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def extract_news_items(html: str, base_url: str, *, max_items: int = CATALOG_SYNTHETIC_MAX_ITEMS) -> list[NewsItem]:
    """Extract repeating news items from a newsroom page.

    Heuristic: ``<article>``/``<li>`` nodes whose heading (or first anchor) links within the
    entity's own domain are treated as items.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_host = domain_from_url(base_url)
    items: list[NewsItem] = []
    seen: set[str] = set()
    for node in soup.find_all(["article", "li"]):
        if not isinstance(node, Tag):
            continue
        anchor = _heading_link(node)
        if anchor is None:
            continue
        href = anchor.get("href")
        title = anchor.get_text(strip=True)
        if not isinstance(href, str) or not href or not title:
            continue
        url = urljoin(base_url, href)
        if not is_domain_aligned(domain_from_url(url), base_host) or url in seen:
            continue
        seen.add(url)
        items.append(NewsItem(title=title, url=url, published_at=_parse_datetime(node)))
        if len(items) >= max_items:
            break
    return items


def build_atom_feed(
    *,
    feed_id: str,
    title: str,
    site_url: str,
    self_url: str,
    items: Sequence[NewsItem],
    updated: datetime | None = None,
) -> str:
    """Serialize extracted items into a valid Atom 1.0 document."""
    now = (updated or datetime.now(timezone.utc)).isoformat()
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"<id>urn:uuid:{escape(feed_id)}</id>",
        f"<title>{escape(title)}</title>",
        f'<link rel="self" href={quoteattr(self_url)}/>',
        f'<link rel="alternate" href={quoteattr(site_url)}/>',
        f"<updated>{now}</updated>",
    ]
    for item in items:
        item_updated = (item.published_at or updated or datetime.now(timezone.utc)).isoformat()
        lines.extend(
            [
                "<entry>",
                f"<id>{escape(item.url)}</id>",
                f"<title>{escape(item.title)}</title>",
                f'<link rel="alternate" href={quoteattr(item.url)}/>',
                f"<updated>{item_updated}</updated>",
                "</entry>",
            ]
        )
    lines.append("</feed>")
    return "\n".join(lines)


async def render_html_with_browser(url: str) -> str | None:
    """Render a page with Playwright. No-op unless ``SYNTHETIC_USE_BROWSER`` is enabled."""
    if not get_settings().SYNTHETIC_USE_BROWSER:
        return None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("SYNTHETIC_USE_BROWSER is set but playwright is not installed")
        return None
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            await page.goto(
                url,
                wait_until="networkidle",
                timeout=CATALOG_CONNECTOR_TIMEOUT * 1000,
            )
            content: str = await page.content()
            await browser.close()
            return content
    except Exception as exc:  # noqa: BLE001 - any render failure just falls back to no content
        logger.warning("Browser render failed", url=url, error=str(exc))
        return None


async def render_synthetic_feed(session_factory: SessionFactory, catalog_feed_id: UUID) -> str | None:
    """Build (and briefly cache) the Atom document for a synthetic catalog feed."""
    cache_key = f"catalog_synthetic:{catalog_feed_id}"
    cached = await redis_cache.get(cache_key)
    if isinstance(cached, str):
        return cached

    async with session_factory() as db:
        feed = await feed_crud.get_catalog_feed_by_id(db, feed_id=catalog_feed_id)
        if not feed or feed.feed_type is not CatalogFeedType.SYNTHETIC_HTML:
            return None
        entity = await entity_crud.get_entity_by_id(db, entity_id=feed.entity_id)
        if not entity:
            return None
        source_url = str(feed.feed_url)
        feed_id = str(feed.id)
        feed_title = entity.name
        site_url = f"https://{entity.canonical_domain}"

    html = await fetching.fetch_page_html(source_url)
    if not html:
        html = await render_html_with_browser(source_url)
    if not html:
        return None

    items = extract_news_items(html, source_url)
    if len(items) < CATALOG_SYNTHETIC_MIN_ITEMS:
        rendered = await render_html_with_browser(source_url)
        if rendered:
            items = extract_news_items(rendered, source_url)
    if not items:
        return None

    atom = build_atom_feed(
        feed_id=feed_id,
        title=feed_title,
        site_url=site_url,
        self_url=build_synthetic_feed_url(catalog_feed_id),
        items=items,
    )
    await redis_cache.set(cache_key, atom, ttl_seconds=CATALOG_SYNTHETIC_CACHE_TTL_SECONDS)
    return atom
