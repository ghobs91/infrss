"""Unit tests for the user-facing feed finder (pure logic and mocked network only)."""

import pytest

from app.services.feeds import discovery
from app.services.feeds.feed_detection import (
    FeedFormat,
    detect_feed_format,
    extract_feed_link_tags,
)

RSS_DOCUMENT = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example News</title>
<item><title>First</title><link>https://example.com/one</link></item>
</channel></rss>"""

ATOM_DOCUMENT = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Example Atom</title></feed>"""


def _resource(body: str, url: str) -> dict:
    """Build the DownloadedResource shape returned by fetching.fetch_public_resource."""
    return {"body": body.encode("utf-8"), "final_url": url, "charset": "utf-8"}


# ===================== Document detection =====================


@pytest.mark.unit
def test_detect_feed_format_recognises_rss_atom_and_json():
    assert detect_feed_format(RSS_DOCUMENT) is FeedFormat.RSS
    assert detect_feed_format(ATOM_DOCUMENT) is FeedFormat.ATOM
    assert detect_feed_format('{"version": "https://jsonfeed.org/version/1.1", "items": []}') is FeedFormat.JSON
    assert detect_feed_format("<html><body>hello</body></html>") is None
    assert detect_feed_format('{"hello": "world"}') is None
    assert detect_feed_format("") is None


@pytest.mark.unit
def test_extract_feed_link_tags_resolves_relative_hrefs():
    html = """
    <html><head>
      <link rel="alternate" type="application/rss+xml" title="Blog" href="/blog/feed.xml">
      <link rel="alternate" type="application/atom+xml" href="https://example.com/atom.xml">
      <link rel="alternate" type="application/feed+json" href="/feed.json">
      <link rel="alternate" type="text/html" href="/index.html">
    </head></html>
    """
    links = extract_feed_link_tags(html, "https://example.com/blog")

    assert [link.url for link in links] == [
        "https://example.com/blog/feed.xml",
        "https://example.com/atom.xml",
        "https://example.com/feed.json",
    ]
    assert [link.format for link in links] == [FeedFormat.RSS, FeedFormat.ATOM, FeedFormat.JSON]
    assert links[0].title == "Blog"


# ===================== URL planning =====================


@pytest.mark.unit
def test_normalize_input_url_adds_scheme_only_when_missing():
    assert discovery.normalize_input_url("example.com/blog") == "https://example.com/blog"
    assert discovery.normalize_input_url("http://example.com") == "http://example.com"
    assert discovery.normalize_input_url("rsshub://github/issue/1") == "rsshub://github/issue/1"


@pytest.mark.unit
def test_build_base_url_strips_query_and_trailing_slash():
    assert discovery.build_base_url("https://example.com/blog/?page=2") == "https://example.com/blog"
    assert discovery.build_base_url("example.com") == "https://example.com"


@pytest.mark.unit
def test_parent_page_urls_walk_up_the_path_to_the_origin():
    assert discovery.parent_page_urls("https://example.com/hub/blog") == [
        "https://example.com/hub",
        "https://example.com",
    ]
    assert discovery.parent_page_urls("https://example.com/") == []


@pytest.mark.unit
def test_parent_page_urls_are_capped():
    parents = discovery.parent_page_urls("https://example.com/a/b/c/d/e", limit=2)
    assert parents == ["https://example.com/a/b/c/d", "https://example.com/a/b/c"]


@pytest.mark.unit
def test_plan_suffix_probes_dedupes_and_can_add_query_suffixes():
    probes = discovery.plan_suffix_probes(
        ["https://example.com/blog", "https://example.com/blog/"],
        ("/feed", "/rss", "/feed"),
        include_query_suffixes=True,
    )

    assert probes == [
        "https://example.com/blog/feed",
        "https://example.com/blog/rss",
        "https://example.com/blog?feed=rss2",
        "https://example.com/blog?feed=atom",
        "https://example.com/blog?format=rss",
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/feed", True),
        ("https://example.com/rss.xml", True),
        ("https://example.com/blog/atom.xml", True),
        ("https://example.com?feed=rss2", True),
        ("https://example.com/about", False),
        ("https://example.com/sitemap.xml", False),
        ("https://example.com/image.xsl", False),
    ],
)
def test_looks_like_feed_url(url, expected):
    assert discovery.looks_like_feed_url(url) is expected


# ===================== Page scanning =====================


@pytest.mark.unit
def test_extract_feed_candidate_links_keeps_only_same_host_feed_links():
    html = """
    <html><body>
      <a href="/feed">RSS</a>
      <a href="https://example.com/rss.xml">RSS again</a>
      <a href="https://other.example/feed">Other site</a>
      <a href="/about">About</a>
      <a href="/sitemap.xml">Sitemap</a>
    </body></html>
    """
    links = discovery.extract_feed_candidate_links(html, "https://example.com/blog")

    assert links == ["https://example.com/feed", "https://example.com/rss.xml"]


@pytest.mark.unit
def test_extract_blog_section_urls_finds_blog_and_news_anchors():
    html = """
    <html><body>
      <a href="/blog">Blog</a>
      <a href="/news/latest">News</a>
      <a href="/pricing">Pricing</a>
      <a href="https://elsewhere.example/blog">Other blog</a>
    </body></html>
    """
    sections = discovery.extract_blog_section_urls(html, "https://example.com")

    assert sections == ["https://example.com/blog", "https://example.com/news/latest"]


@pytest.mark.unit
def test_detect_platform_from_generator_and_markup_markers():
    wordpress = '<html><head><meta name="generator" content="WordPress 6.5"></head></html>'
    ghost = '<html><body><script src="https://content.ghost.io/x.js"></script></body></html>'
    plain = "<html><body>No platform here</body></html>"

    assert discovery.detect_platform(wordpress) == "wordpress"
    assert discovery.detect_platform(ghost) == "ghost"
    assert discovery.detect_platform(plain) is None


@pytest.mark.unit
def test_sitemap_parsing_helpers():
    robots = "User-agent: *\nDisallow:\nSitemap: https://example.com/sitemap.xml\n"
    sitemap = """<?xml version="1.0"?><urlset>
        <url><loc>https://example.com/feed.xml</loc></url>
        <url><loc>https://example.com/about</loc></url>
        <url><loc>https://example.com/rss</loc></url>
    </urlset>"""

    assert discovery.parse_robots_sitemaps(robots) == ["https://example.com/sitemap.xml"]
    assert discovery.feed_urls_from_locations(discovery.parse_sitemap_locations(sitemap)) == [
        "https://example.com/feed.xml",
        "https://example.com/rss",
    ]


@pytest.mark.unit
class TestThirdPartyOwnership:
    """A guessed third-party feed URL must belong to the requested site."""

    @pytest.mark.parametrize(
        ("feed_host", "site_link", "expected"),
        [
            ("https://feeds.feedburner.com/example.com", "https://example.com", True),
            ("https://feeds.feedburner.com/example.com", "https://blog.example.com", True),
            ("https://feeds.feedburner.com/example.com", "https://www.example.com/", True),
            ("https://feeds.feedburner.com/example.com", "https://example.net.cn", False),
            ("https://feeds.feedburner.com/example.com", None, False),
        ],
    )
    def test_host_alignment_gate(self, feed_host, site_link, expected):
        rss = (
            RSS_DOCUMENT
            if site_link is None
            else RSS_DOCUMENT.replace("<channel>", f"<channel><link>{site_link}</link>")
        )
        candidate = discovery.FeedCandidate(url=feed_host, content=rss, format=FeedFormat.RSS)
        assert discovery._candidate_belongs_to_site(candidate, "example.com") is expected


# ===================== Orchestration =====================


def _patch_fetching(monkeypatch, pages: dict[str, str], probes: list[str] | None = None):
    """Serve both fetch paths from one URL map, recording the probe fetches."""

    async def fake_fetch_content(url, **_kwargs):
        body = pages.get(url)
        return {
            "content": body or "",
            "headers": {},
            "status_code": 200 if body else 502,
            "not_modified": False,
            "error": None if body else "HTTP 502",
            "final_url": url,
            "permanent_redirect": False,
        }

    async def fake_fetch_public_resource(url, *, timeout=None, max_bytes=None):
        if probes is not None:
            probes.append(url)
        body = pages.get(url)
        return _resource(body, url) if body else None

    monkeypatch.setattr(discovery.fetching, "fetch_feed_content", fake_fetch_content)
    monkeypatch.setattr(discovery.fetching, "fetch_public_resource", fake_fetch_public_resource)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_stops_when_the_url_is_already_a_feed(monkeypatch):
    probes: list[str] = []
    _patch_fetching(monkeypatch, {"https://example.com/feed.xml": RSS_DOCUMENT}, probes)

    report = await discovery.discover_feeds_for_url("https://example.com/feed.xml")

    assert report.is_direct_feed is True
    assert [candidate.title for candidate in report.candidates] == ["Example News"]
    assert probes == []
    assert report.steps[0].key is discovery.DiscoveryStepKey.DIRECT
    assert report.steps[0].status is discovery.DiscoveryStepStatus.OK
    assert report.steps[0].found == 1
    assert all(step.status is discovery.DiscoveryStepStatus.SKIPPED for step in report.steps[1:])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_reads_feed_declarations_from_the_page(monkeypatch):
    page = """<html><head>
        <link rel="alternate" type="application/rss+xml" href="/feed.xml">
    </head><body><a href="/about">About</a></body></html>"""
    _patch_fetching(
        monkeypatch,
        {
            "https://example.com/blog": page,
            "https://example.com/feed.xml": ATOM_DOCUMENT,
        },
    )

    report = await discovery.discover_feeds_for_url("https://example.com/blog")

    assert report.is_direct_feed is False
    assert [candidate.url for candidate in report.candidates] == ["https://example.com/feed.xml"]
    assert report.steps[0].status is discovery.DiscoveryStepStatus.OK
    assert report.steps[1].key is discovery.DiscoveryStepKey.AUTODISCOVERY
    assert report.steps[1].found == 1
    assert all(step.status is discovery.DiscoveryStepStatus.SKIPPED for step in report.steps[2:])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_falls_through_to_common_suffixes(monkeypatch):
    _patch_fetching(
        monkeypatch,
        {
            "https://example.com": "<html><body>no feeds advertised</body></html>",
            "https://example.com/feed": RSS_DOCUMENT,
        },
    )

    report = await discovery.discover_feeds_for_url("https://example.com")

    assert [candidate.url for candidate in report.candidates] == ["https://example.com/feed"]
    executed = [step for step in report.steps if step.status is not discovery.DiscoveryStepStatus.SKIPPED]
    assert executed[-1].key is discovery.DiscoveryStepKey.SUFFIXES
    assert executed[-1].found == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discovery_records_a_failed_step_and_continues(monkeypatch):
    async def failing_stage(run):
        raise RuntimeError("kaboom")

    _patch_fetching(monkeypatch, {"https://example.com": "<html><body>quiet site</body></html>"})
    monkeypatch.setattr(
        discovery,
        "STAGES",
        (
            (discovery.DiscoveryStepKey.DIRECT, discovery.stage_direct),
            (discovery.DiscoveryStepKey.AUTODISCOVERY, failing_stage),
        ),
    )

    report = await discovery.discover_feeds_for_url("https://example.com")

    assert report.candidates == []
    assert [step.status for step in report.steps] == [
        discovery.DiscoveryStepStatus.OK,
        discovery.DiscoveryStepStatus.FAILED,
    ]
