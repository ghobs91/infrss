"""Feed document detection and HTML feed-link extraction.

Shared by every discovery path: the catalog's autodiscovery sweep, the user-facing feed finder,
and any caller that needs to answer "is this body a feed?" or "which feeds does this page
advertise?" without caring about the surrounding business logic.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag


class FeedFormat(str, Enum):
    """Serialisation format of a feed document."""

    RSS = "rss"
    ATOM = "atom"
    JSON = "json"


# ``<link type="...">`` MIME types that identify a feed document.
FEED_LINK_MIME_TYPES: dict[str, FeedFormat] = {
    "application/rss+xml": FeedFormat.RSS,
    "application/atom+xml": FeedFormat.ATOM,
    "application/feed+json": FeedFormat.JSON,
}

_RSS_MARKER = re.compile(r"<\s*(rss|rdf:RDF)\b", re.IGNORECASE)
_ATOM_MARKER = re.compile(r"<\s*feed\b", re.IGNORECASE)
_JSONFEED_VERSION = re.compile(r"jsonfeed", re.IGNORECASE)
_ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
_HEAD_BYTES = 4096


@dataclass(frozen=True)
class FeedLink:
    """A feed declaration found in an HTML page's ``<link rel="alternate">`` tags."""

    url: str
    format: FeedFormat
    title: str | None = None


def detect_feed_format(content: str | None) -> FeedFormat | None:
    """Classify a document as RSS, Atom or JSON Feed; ``None`` when it is none of them."""
    if not content:
        return None

    document = content.lstrip("\ufeff \t\r\n")
    head = document[:_HEAD_BYTES]
    if head.startswith("{"):
        # Only the version marker is inspected: a feed body can be tens of megabytes, so the
        # whole document is never parsed just to classify it.
        return FeedFormat.JSON if _JSONFEED_VERSION.search(head) else None
    if _ATOM_NAMESPACE in head:
        return FeedFormat.ATOM
    if _RSS_MARKER.search(head):
        return FeedFormat.RSS
    if _ATOM_MARKER.search(head):
        return FeedFormat.ATOM
    return None


def extract_feed_link_tags(html: str, base_url: str) -> list[FeedLink]:
    """Extract RSS/Atom/JSON Feed ``<link rel="alternate">`` declarations from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[FeedLink] = []
    for tag in soup.find_all("link"):
        if not isinstance(tag, Tag):
            continue
        rel_value: Any = tag.get("rel") or []
        rel_list: list[str] = (
            [rel_value] if isinstance(rel_value, str) else [v for v in rel_value if isinstance(v, str)]
        )
        if "alternate" not in [value.lower() for value in rel_list]:
            continue
        feed_format = FEED_LINK_MIME_TYPES.get(str(tag.get("type", "")).lower().strip())
        href = tag.get("href")
        if not feed_format or not isinstance(href, str) or not href.strip():
            continue
        title = tag.get("title")
        links.append(
            FeedLink(
                url=urljoin(base_url, href.strip()),
                format=feed_format,
                title=title if isinstance(title, str) else None,
            )
        )
    return links
