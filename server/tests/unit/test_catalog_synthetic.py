"""Unit tests for synthetic feed extraction and Atom generation (no network)."""

import feedparser
import pytest

from app.services.catalog.synthetic import NewsItem, build_atom_feed, extract_news_items

_NEWSROOM_HTML = """
<html><body>
<article><h2><a href="/news/first">First release</a></h2><time datetime="2026-01-02T10:00:00Z"></time></article>
<article><h2><a href="https://example.com/news/second">Second release</a></h2></article>
<article><h2><a href="https://other.com/external">Off site</a></h2></article>
<li><h3><a href="/news/third">Third release</a></h3></li>
</body></html>
"""


@pytest.mark.unit
def test_extract_news_items_filters_offsite_and_keeps_document_order():
    items = extract_news_items(_NEWSROOM_HTML, "https://example.com/newsroom")
    assert [item.url for item in items] == [
        "https://example.com/news/first",
        "https://example.com/news/second",
        "https://example.com/news/third",
    ]
    assert items[0].published_at is not None


@pytest.mark.unit
def test_extract_news_items_respects_max_items():
    html = "".join(f'<article><h2><a href="/news/{i}">Item {i}</a></h2></article>' for i in range(10))
    assert len(extract_news_items(html, "https://example.com", max_items=4)) == 4


@pytest.mark.unit
def test_build_atom_feed_is_valid_atom():
    atom = build_atom_feed(
        feed_id="11111111-1111-1111-1111-111111111111",
        title="Example Corp",
        site_url="https://example.com",
        self_url="http://localhost:8008/api/catalog/synthetic/11111111-1111-1111-1111-111111111111.atom",
        items=[NewsItem(title="Alpha", url="https://example.com/a")],
    )
    parsed = feedparser.parse(atom)
    assert parsed.version.startswith("atom")
    assert parsed.feed.title == "Example Corp"
    assert len(parsed.entries) == 1
    assert parsed.entries[0].link == "https://example.com/a"
    assert parsed.entries[0].id == "https://example.com/a"


@pytest.mark.unit
def test_build_atom_feed_escapes_special_characters():
    atom = build_atom_feed(
        feed_id="22222222-2222-2222-2222-222222222222",
        title="R&D <Group>",
        site_url="https://example.com",
        self_url="https://example.com/feed.atom",
        items=[NewsItem(title="A & B <test>", url="https://example.com/x?a=1&b=2")],
    )
    parsed = feedparser.parse(atom)
    assert parsed.feed.title == "R&D <Group>"
    assert parsed.entries[0].title == "A & B <test>"
