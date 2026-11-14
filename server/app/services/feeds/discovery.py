"""Find the feeds a website publishes, for a URL pasted into Discover.

The ladder mirrors a web feed finder: treat the URL as a feed, then read the page and its parent
pages for ``<link rel="alternate">`` declarations, scan outbound links and the sitemap, probe
well-known feed suffixes, follow blog-platform hints, and finally try third-party feed hosts.

Stages run in order and stop at the first one that yields a verified feed, so a typical lookup only
makes a handful of requests while an uncooperative site still gets the full sweep (bounded by
:data:`FEED_DISCOVERY_BUDGET_SECONDS`). Every outbound request goes through the SSRF-safe helpers in
:mod:`app.services.feeds.fetching`.
"""

import asyncio
import re
import time
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urljoin, urlparse, urlunparse

import structlog
from bs4 import BeautifulSoup, Tag

from app.core.constants import (
    FEED_DISCOVERY_BLOG_PATHS,
    FEED_DISCOVERY_BLOG_SUFFIXES,
    FEED_DISCOVERY_BUDGET_SECONDS,
    FEED_DISCOVERY_CONCURRENCY,
    FEED_DISCOVERY_MAX_BLOG_SECTIONS,
    FEED_DISCOVERY_MAX_LINK_CANDIDATES,
    FEED_DISCOVERY_MAX_PAGE_BYTES,
    FEED_DISCOVERY_MAX_PARENT_PAGES,
    FEED_DISCOVERY_MAX_RESULTS,
    FEED_DISCOVERY_MAX_SITEMAP_CANDIDATES,
    FEED_DISCOVERY_PLATFORM_SUFFIXES,
    FEED_DISCOVERY_PROBE_TIMEOUT_SECONDS,
    FEED_DISCOVERY_QUERY_SUFFIXES,
    FEED_DISCOVERY_SUFFIXES,
    FEED_DISCOVERY_THIRD_PARTY_URLS,
)
from app.services.feeds import fetching, parsing
from app.services.feeds.feed_detection import (
    FeedFormat,
    detect_feed_format,
    extract_feed_link_tags,
)
from app.utils.urls import normalize_feed_url

logger = structlog.get_logger(__name__)

_FEED_HREF_HINT = re.compile(r"(^|[/_.-])(rss|atom|feed)([/_.-]|$)|\.(rss|atom|xml)$", re.IGNORECASE)
_FEED_QUERY_HINT = re.compile(r"(^|&)(feed|format|output)=(rss|rss2|atom|xml)", re.IGNORECASE)
_NON_FEED_XML = re.compile(r"sitemap|robots|opml|\.xsl$", re.IGNORECASE)
_ROBOTS_SITEMAP = re.compile(r"(?im)^\s*sitemap:\s*(\S+)\s*$")
_XML_LOCATION = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)
_PLATFORM_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wordpress", ("wp-content", "wp-json", "wordpress")),
    ("ghost", ("ghost.org", "ghost-", "content.ghost")),
    ("substack", ("substackcdn", "substack.com")),
    ("blogger", ("blogspot", "blogger.com", "www.blogger")),
    ("medium", ("medium.com",)),
    ("squarespace", ("squarespace", "static1.squarespace")),
)


class DiscoveryStepKey(str, Enum):
    """One strategy in the discovery ladder."""

    DIRECT = "direct"
    AUTODISCOVERY = "autodiscovery"
    AUTODISCOVERY_PARENT = "autodiscovery_parent"
    SITE_LINKS = "site_links"
    SITEMAP = "sitemap"
    SUFFIXES = "suffixes"
    PARENT_SUFFIXES = "parent_suffixes"
    BLOG_META = "blog_meta"
    BLOG_SUFFIXES = "blog_suffixes"
    THIRD_PARTY = "third_party"


class DiscoveryStepStatus(str, Enum):
    """Outcome of a single strategy."""

    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"


STEP_LABELS: dict[DiscoveryStepKey, str] = {
    DiscoveryStepKey.DIRECT: "Checking feed",
    DiscoveryStepKey.AUTODISCOVERY: "Checking RSS autodiscovery",
    DiscoveryStepKey.AUTODISCOVERY_PARENT: "Checking RSS autodiscovery in parent pages",
    DiscoveryStepKey.SITE_LINKS: "Searching all website links",
    DiscoveryStepKey.SITEMAP: "Searching sitemap",
    DiscoveryStepKey.SUFFIXES: "Searching common suffixes",
    DiscoveryStepKey.PARENT_SUFFIXES: "Searching common suffixes in parent pages",
    DiscoveryStepKey.BLOG_META: "Searching blog meta tags",
    DiscoveryStepKey.BLOG_SUFFIXES: "Searching blog common suffixes",
    DiscoveryStepKey.THIRD_PARTY: "Searching 3rd party feeds",
}


@dataclass(frozen=True)
class FeedCandidate:
    """A verified feed document found during a run."""

    url: str
    content: str
    format: FeedFormat
    title: str | None = None


@dataclass(frozen=True)
class DiscoveryStepResult:
    """What one strategy in the ladder did."""

    key: DiscoveryStepKey
    label: str
    status: DiscoveryStepStatus
    found: int = 0


@dataclass(frozen=True)
class FeedDiscoveryReport:
    """Result of a discovery run for one input URL."""

    input_url: str
    base_url: str
    is_direct_feed: bool = False
    candidates: list[FeedCandidate] = field(default_factory=list)
    steps: list[DiscoveryStepResult] = field(default_factory=list)


class DiscoveryRun:
    """Mutable state shared by the stages of one run."""

    def __init__(self, url: str) -> None:
        self.input_url = normalize_input_url(url)
        self.base_url = build_base_url(self.input_url)
        self.origin = site_origin(self.input_url)
        self.is_direct_feed = False
        self.candidates: list[FeedCandidate] = []
        self.steps: list[DiscoveryStepResult] = []
        self.pages: dict[str, str | None] = {}
        self.probed: set[str] = set()
        self._seen_titles: set[tuple[str, str]] = set()
        self.deadline = time.monotonic() + FEED_DISCOVERY_BUDGET_SECONDS

    def expired(self) -> bool:
        """Whether the run has used up its request budget."""
        return time.monotonic() >= self.deadline

    def remaining(self) -> float:
        """Seconds left in the run's request budget."""
        return max(0.0, self.deadline - time.monotonic())

    def claim_probe(self, url: str) -> bool:
        """Reserve a URL for probing; ``False`` when it has already been probed."""
        key = normalize_feed_url(url)
        if not key or key in self.probed:
            return False
        self.probed.add(key)
        return True

    def remember(self, candidates: Iterable[FeedCandidate]) -> None:
        """Add newly verified candidates, dropping duplicates."""
        for candidate in candidates:
            identity = (normalize_feed_url(candidate.url), (candidate.title or "").strip().lower())
            if identity in self._seen_titles:
                continue
            self._seen_titles.add(identity)
            self.candidates.append(candidate)

    def loaded_pages(self) -> list[tuple[str, str]]:
        """Pages successfully fetched so far, as ``(url, html)`` pairs."""
        return [(url, html) for url, html in self.pages.items() if html]


StageFn = Callable[[DiscoveryRun], Awaitable[list[FeedCandidate]]]


# ===================== Pure URL / HTML helpers =====================


def normalize_input_url(url: str) -> str:
    """Give a bare domain an ``https://`` scheme and leave explicitly-schemed URLs alone."""
    candidate = (url or "").strip()
    if not candidate:
        return candidate
    if "://" in candidate:
        return candidate
    return f"https://{candidate}"


def site_origin(url: str) -> str:
    """``scheme://host`` for a URL, with no path, query or fragment."""
    parsed = urlparse(normalize_input_url(url))
    if not parsed.netloc:
        return normalize_input_url(url)
    return urlunparse((parsed.scheme or "https", parsed.netloc, "", "", "", ""))


def build_base_url(url: str) -> str:
    """Normalize a URL to a probe base: scheme + host + path, without query or trailing slash."""
    candidate = normalize_input_url(url)
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return candidate
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", "", ""))


def parent_page_urls(url: str, limit: int = FEED_DISCOVERY_MAX_PARENT_PAGES) -> list[str]:
    """Ancestors of a page URL, nearest first, ending at the site origin."""
    parsed = urlparse(normalize_input_url(url))
    origin = site_origin(url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    ancestors: list[str] = []
    for cut in range(len(segments) - 1, -1, -1):
        path = "/".join(segments[:cut])
        ancestors.append(f"{origin}/{path}" if path else origin)
        if len(ancestors) >= limit:
            break
    return ancestors


def plan_suffix_probes(
    bases: Sequence[str], suffixes: Sequence[str], include_query_suffixes: bool = False
) -> list[str]:
    """Build ``base + suffix`` probe URLs, deduplicated and order-preserving."""
    planned: list[str] = []
    seen: set[str] = set()
    for base in bases:
        trimmed = base.rstrip("/")
        if not trimmed:
            continue
        candidates = [f"{trimmed}{suffix}" for suffix in suffixes]
        if include_query_suffixes:
            candidates.extend(f"{trimmed}{suffix}" for suffix in FEED_DISCOVERY_QUERY_SUFFIXES)
        for candidate in candidates:
            key = normalize_feed_url(candidate)
            if key in seen:
                continue
            seen.add(key)
            planned.append(candidate)
    return planned


def looks_like_feed_url(url: str) -> bool:
    """Whether a URL's shape suggests a feed rather than a page or a non-feed XML file."""
    parsed = urlparse(url)
    if _NON_FEED_XML.search(f"{parsed.path}?{parsed.query}"):
        return False
    if parsed.query and _FEED_QUERY_HINT.search(parsed.query):
        return True
    if not parsed.path:
        return False
    return bool(_FEED_HREF_HINT.search(parsed.path))


def extract_feed_candidate_links(
    html: str, base_url: str, limit: int = FEED_DISCOVERY_MAX_LINK_CANDIDATES
) -> list[str]:
    """Collect anchors from a page whose href looks like a feed endpoint."""
    soup = BeautifulSoup(html, "html.parser")
    origin = site_origin(base_url)
    found: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a"):
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        url = urljoin(base_url, href.strip())
        if site_origin(url) != origin or not looks_like_feed_url(url):
            continue
        key = normalize_feed_url(url)
        if key in seen:
            continue
        seen.add(key)
        found.append(url)
        if len(found) >= limit:
            break
    return found


def extract_blog_section_urls(html: str, base_url: str, limit: int = FEED_DISCOVERY_MAX_BLOG_SECTIONS) -> list[str]:
    """Collect anchors that point at a blog/news style section of the same site."""
    soup = BeautifulSoup(html, "html.parser")
    origin = site_origin(base_url)
    found: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a"):
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        if not isinstance(href, str) or not href.strip():
            continue
        url = urljoin(base_url, href.strip())
        if site_origin(url) != origin:
            continue
        path = urlparse(url).path.rstrip("/").lower()
        if not any(path == section or path.startswith(f"{section}/") for section in FEED_DISCOVERY_BLOG_PATHS):
            continue
        key = normalize_feed_url(build_base_url(url))
        if key in seen:
            continue
        seen.add(key)
        found.append(build_base_url(url))
        if len(found) >= limit:
            break
    return found


def detect_platform(html: str) -> str | None:
    """Identify the publishing platform behind a page from its markup."""
    soup = BeautifulSoup(html, "html.parser")
    generator = soup.find("meta", attrs={"name": re.compile("^generator$", re.IGNORECASE)})
    generator_value = ""
    if isinstance(generator, Tag):
        generator_value = str(generator.get("content") or "").lower()
    haystack = f"{generator_value} {html[:40000].lower()}"
    for platform, markers in _PLATFORM_MARKERS:
        if any(marker in haystack for marker in markers):
            return platform
    return None


def host_without_www(url: str) -> str:
    """Lowercased hostname of a URL (or bare host), with a leading ``www.`` removed."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path).lower()
    return host[4:] if host.startswith("www.") else host


def is_host_aligned(host: str, site_host: str) -> bool:
    """Whether a feed's host belongs to the site (or the site to the feed's host)."""
    if not host or not site_host:
        return False
    return host == site_host or host.endswith(f".{site_host}") or site_host.endswith(f".{host}")


def parse_robots_sitemaps(text: str) -> list[str]:
    """Extract ``Sitemap:`` declarations from a robots.txt body."""
    return [match.strip() for match in _ROBOTS_SITEMAP.findall(text or "")]


def parse_sitemap_locations(text: str) -> list[str]:
    """Extract ``<loc>`` entries from a sitemap or sitemap index body."""
    return [match.strip() for match in _XML_LOCATION.findall(text or "")]


def feed_urls_from_locations(locations: Sequence[str], limit: int = FEED_DISCOVERY_MAX_SITEMAP_CANDIDATES) -> list[str]:
    """Keep the sitemap locations that look like feeds."""
    feeds: list[str] = []
    seen: set[str] = set()
    for location in locations:
        if not looks_like_feed_url(location):
            continue
        key = normalize_feed_url(location)
        if key in seen:
            continue
        seen.add(key)
        feeds.append(location)
        if len(feeds) >= limit:
            break
    return feeds


# ===================== Network helpers =====================


async def probe_feed(url: str, run: DiscoveryRun, semaphore: asyncio.Semaphore) -> FeedCandidate | None:
    """Fetch ``url`` and return it as a candidate only when it really serves a feed document."""
    if run.expired():
        return None
    async with semaphore:
        if not run.claim_probe(url):
            return None
        resource = await fetching.fetch_public_resource(
            url, timeout=FEED_DISCOVERY_PROBE_TIMEOUT_SECONDS, max_bytes=FEED_DISCOVERY_MAX_PAGE_BYTES
        )
        if resource is None:
            return None
        content = fetching.decode_resource(resource)
        feed_format = detect_feed_format(content)
        if feed_format is None:
            return None
        final_url = resource["final_url"] or url
        return FeedCandidate(
            url=final_url,
            content=content,
            format=feed_format,
            title=parsing.extract_feed_title(content),
        )


async def probe_feeds(urls: Sequence[str], run: DiscoveryRun) -> list[FeedCandidate]:
    """Probe candidate URLs concurrently, keeping only the ones that are feeds."""
    if not urls or run.expired():
        return []
    semaphore = asyncio.Semaphore(FEED_DISCOVERY_CONCURRENCY)
    tasks = [probe_feed(url, run, semaphore) for url in urls]
    try:
        results: Sequence[object] = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True), timeout=run.remaining()
        )
    except asyncio.TimeoutError:
        logger.info("Feed discovery probes hit the run budget", target=run.base_url, probes=len(urls))
        return []
    return _collect_candidates(results, run.base_url)


def _collect_candidates(results: Sequence[object], target: str) -> list[FeedCandidate]:
    """Flatten probe results, logging and dropping failures."""
    candidates: list[FeedCandidate] = []
    for result in results:
        if isinstance(result, FeedCandidate):
            candidates.append(result)
        elif isinstance(result, BaseException):
            logger.debug("Feed discovery probe failed", target=target, error=str(result))
    return candidates


async def load_page(url: str, run: DiscoveryRun, semaphore: asyncio.Semaphore | None = None) -> str | None:
    """Fetch and cache a page's HTML for the duration of the run."""
    key = normalize_feed_url(url)
    if key in run.pages:
        return run.pages[key]
    if run.expired():
        return None
    if semaphore is None:
        html = await fetching.fetch_page_html(
            url, timeout=FEED_DISCOVERY_PROBE_TIMEOUT_SECONDS, max_bytes=FEED_DISCOVERY_MAX_PAGE_BYTES
        )
    else:
        async with semaphore:
            html = await fetching.fetch_page_html(
                url, timeout=FEED_DISCOVERY_PROBE_TIMEOUT_SECONDS, max_bytes=FEED_DISCOVERY_MAX_PAGE_BYTES
            )
    run.pages[key] = html
    return html


async def load_pages(urls: Sequence[str], run: DiscoveryRun) -> list[tuple[str, str]]:
    """Fetch several pages concurrently and return the successful ``(url, html)`` pairs."""
    pending = [url for url in urls if normalize_feed_url(url) not in run.pages]
    if pending:
        semaphore = asyncio.Semaphore(FEED_DISCOVERY_CONCURRENCY)
        results = await asyncio.gather(*(load_page(url, run, semaphore) for url in pending), return_exceptions=True)
        for result in results:
            if isinstance(result, BaseException):
                logger.debug("Feed discovery page fetch failed", target=run.base_url, error=str(result))
    pages: list[tuple[str, str]] = []
    for url in urls:
        html = run.pages.get(normalize_feed_url(url))
        if html:
            pages.append((url, html))
    return pages


# ===================== Stages =====================


async def stage_direct(run: DiscoveryRun) -> list[FeedCandidate]:
    """Treat the input URL itself as a feed, caching the body when it is a page instead."""
    if run.expired():
        return []
    # fetch_feed_content is used (rather than the raw resource helper) so an ``rsshub://`` input
    # is translated to the configured RSSHub instance first.
    result = await fetching.fetch_feed_content(run.input_url)
    if result["error"] or not result["content"]:
        return []
    content = result["content"]
    feed_format = detect_feed_format(content)
    if feed_format is not None:
        run.is_direct_feed = True
        final_url = result["final_url"] or run.input_url
        return [
            FeedCandidate(
                url=final_url,
                content=content,
                format=feed_format,
                title=parsing.extract_feed_title(content),
            )
        ]
    run.pages[normalize_feed_url(run.input_url)] = content
    return []


async def stage_autodiscovery(run: DiscoveryRun) -> list[FeedCandidate]:
    """Read ``<link rel="alternate">`` declarations on the input page."""
    pages = await load_pages([run.input_url], run)
    return await _probe_link_tags(pages, run)


async def stage_autodiscovery_parent(run: DiscoveryRun) -> list[FeedCandidate]:
    """Read feed declarations on the input page's ancestor pages."""
    pages = await load_pages(parent_page_urls(run.input_url), run)
    return await _probe_link_tags(pages, run)


async def _probe_link_tags(pages: Sequence[tuple[str, str]], run: DiscoveryRun) -> list[FeedCandidate]:
    """Verify the feeds advertised by a set of already-fetched pages."""
    urls: list[str] = []
    for page_url, html in pages:
        urls.extend(link.url for link in extract_feed_link_tags(html, page_url))
    return await probe_feeds(urls, run)


async def stage_site_links(run: DiscoveryRun) -> list[FeedCandidate]:
    """Probe anchors on the pages already read that look like feed endpoints."""
    urls: list[str] = []
    for page_url, html in run.loaded_pages():
        urls.extend(extract_feed_candidate_links(html, page_url))
    return await probe_feeds(urls, run)


async def stage_sitemap(run: DiscoveryRun) -> list[FeedCandidate]:
    """Look for feed URLs declared in robots.txt or the site's sitemaps."""
    sitemap_urls = await _sitemap_sources(run)
    locations: list[str] = []
    for sitemap_url in sitemap_urls:
        resource = await fetching.fetch_public_resource(
            sitemap_url, timeout=FEED_DISCOVERY_PROBE_TIMEOUT_SECONDS, max_bytes=FEED_DISCOVERY_MAX_PAGE_BYTES
        )
        if resource is None:
            continue
        locations.extend(parse_sitemap_locations(fetching.decode_resource(resource)))
        if len(locations) >= FEED_DISCOVERY_MAX_SITEMAP_CANDIDATES * 20:
            break
    return await probe_feeds(feed_urls_from_locations(locations), run)


async def _sitemap_sources(run: DiscoveryRun) -> list[str]:
    """Sitemap URLs advertised by robots.txt, falling back to the conventional filenames."""
    robots = await fetching.fetch_public_resource(
        f"{run.origin}/robots.txt",
        timeout=FEED_DISCOVERY_PROBE_TIMEOUT_SECONDS,
        max_bytes=FEED_DISCOVERY_MAX_PAGE_BYTES,
    )
    declared = parse_robots_sitemaps(fetching.decode_resource(robots)) if robots else []
    sources = declared or [f"{run.origin}/sitemap.xml"]
    if not declared:
        sources.append(f"{run.origin}/sitemap_index.xml")
    return sources[:2]


async def stage_suffixes(run: DiscoveryRun) -> list[FeedCandidate]:
    """Probe well-known feed paths against the input URL."""
    bases = [build_base_url(run.input_url)]
    urls = plan_suffix_probes(bases, FEED_DISCOVERY_SUFFIXES, include_query_suffixes=True)
    return await probe_feeds(urls, run)


async def stage_parent_suffixes(run: DiscoveryRun) -> list[FeedCandidate]:
    """Probe well-known feed paths against the input page's ancestors."""
    urls = plan_suffix_probes(parent_page_urls(run.input_url), FEED_DISCOVERY_SUFFIXES)
    return await probe_feeds(urls, run)


async def stage_blog_meta(run: DiscoveryRun) -> list[FeedCandidate]:
    """Derive feed paths from the CMS identity declared in the page's meta tags."""
    pages = await load_pages([run.input_url], run)
    platform = detect_platform(pages[0][1]) if pages else None
    if not platform:
        return []
    suffixes = FEED_DISCOVERY_PLATFORM_SUFFIXES.get(platform, ())
    if not suffixes:
        return []
    bases = [build_base_url(run.input_url), run.origin]
    return await probe_feeds(plan_suffix_probes(bases, suffixes), run)


async def stage_blog_suffixes(run: DiscoveryRun) -> list[FeedCandidate]:
    """Probe common feed paths against blog/news sections linked from the page."""
    sections: list[str] = []
    seen: set[str] = set()
    for page_url, html in run.loaded_pages():
        for section in extract_blog_section_urls(html, page_url):
            key = normalize_feed_url(section)
            if key in seen:
                continue
            seen.add(key)
            sections.append(section)
    return await probe_feeds(plan_suffix_probes(sections, FEED_DISCOVERY_BLOG_SUFFIXES), run)


async def stage_third_party(run: DiscoveryRun) -> list[FeedCandidate]:
    """
    Probe third-party feed hosts that publish a site's feed under the site's own slug.

    A host serves whoever claimed the slug, so an unclaimed guess can return an unrelated feed.
    Only feeds that declare a site link aligned with the requested host are kept.
    """
    slug = host_without_www(run.origin)
    urls = [template.format(host=slug) for template in FEED_DISCOVERY_THIRD_PARTY_URLS]
    candidates = await probe_feeds(urls, run)
    site_host = host_without_www(run.origin)
    return [candidate for candidate in candidates if _candidate_belongs_to_site(candidate, site_host)]


def _candidate_belongs_to_site(candidate: FeedCandidate, site_host: str) -> bool:
    """Whether a third-party-hosted feed declares a website that matches the requested site."""
    site_link = parsing.extract_feed_site_link(candidate.content)
    return bool(site_link) and is_host_aligned(host_without_www(site_link), site_host)


STAGES: tuple[tuple[DiscoveryStepKey, StageFn], ...] = (
    (DiscoveryStepKey.DIRECT, stage_direct),
    (DiscoveryStepKey.AUTODISCOVERY, stage_autodiscovery),
    (DiscoveryStepKey.AUTODISCOVERY_PARENT, stage_autodiscovery_parent),
    (DiscoveryStepKey.SITE_LINKS, stage_site_links),
    (DiscoveryStepKey.SITEMAP, stage_sitemap),
    (DiscoveryStepKey.SUFFIXES, stage_suffixes),
    (DiscoveryStepKey.PARENT_SUFFIXES, stage_parent_suffixes),
    (DiscoveryStepKey.BLOG_META, stage_blog_meta),
    (DiscoveryStepKey.BLOG_SUFFIXES, stage_blog_suffixes),
    (DiscoveryStepKey.THIRD_PARTY, stage_third_party),
)


# ===================== Orchestration =====================


async def discover_feeds_for_url(url: str, max_results: int = FEED_DISCOVERY_MAX_RESULTS) -> FeedDiscoveryReport:
    """Run the discovery ladder for ``url`` and report every step that was attempted."""
    run = DiscoveryRun(url)
    for index, (key, stage) in enumerate(STAGES):
        if run.candidates:
            _record_skipped(run, STAGES[index:])
            break
        if run.expired():
            logger.info("Feed discovery budget exhausted", url=run.input_url, completed_steps=len(run.steps))
            _record_skipped(run, STAGES[index:])
            break
        step, found = await _run_stage(run, key, stage)
        run.remember(found)
        run.steps.append(step)

    candidates = run.candidates[:max_results]
    logger.info(
        "Feed discovery complete",
        url=run.input_url,
        base_url=run.base_url,
        is_direct_feed=run.is_direct_feed,
        found=len(candidates),
        steps=len(run.steps),
    )
    return FeedDiscoveryReport(
        input_url=run.input_url,
        base_url=run.base_url,
        is_direct_feed=run.is_direct_feed,
        candidates=candidates,
        steps=run.steps,
    )


async def _run_stage(
    run: DiscoveryRun, key: DiscoveryStepKey, stage: StageFn
) -> tuple[DiscoveryStepResult, list[FeedCandidate]]:
    """Execute one stage, converting an unexpected failure into a recorded step."""
    try:
        found = await stage(run)
    except Exception as exc:  # noqa: BLE001 - one broken strategy must not abort the run
        logger.warning("Feed discovery step failed", step=key.value, url=run.input_url, error=str(exc))
        return DiscoveryStepResult(key=key, label=STEP_LABELS[key], status=DiscoveryStepStatus.FAILED), []
    if found:
        logger.debug("Feed discovery step found feeds", step=key.value, url=run.input_url, found=len(found))
    step = DiscoveryStepResult(key=key, label=STEP_LABELS[key], status=DiscoveryStepStatus.OK, found=len(found))
    return step, found


def _record_skipped(run: DiscoveryRun, remaining: Sequence[tuple[DiscoveryStepKey, StageFn]]) -> None:
    """Record the stages that were not attempted, so every step appears in the report."""
    for key, _stage in remaining:
        run.steps.append(DiscoveryStepResult(key=key, label=STEP_LABELS[key], status=DiscoveryStepStatus.SKIPPED))
