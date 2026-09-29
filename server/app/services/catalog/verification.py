"""Catalog verification: poll candidate feeds, apply the gatekeeper, keep the lifecycle moving.

Mirrors the fetch lifecycle used for global feeds, but is gated on ``catalog_feeds.next_poll_at``
rather than subscriber count, and runs the gatekeeper instead of article ingestion.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog

from app.core.constants import (
    CATALOG_MAX_FAILURES,
    CATALOG_QUARANTINE_RECHECK_HOURS,
    CATALOG_VERIFY_BACKOFF_MINUTES,
    CATALOG_VERIFY_INTERVAL_MINUTES,
    MAX_ERROR_BACKOFF_MINUTES,
)
from app.crud.catalog import entities as entity_crud
from app.crud.catalog import feeds as feed_crud
from app.models.catalog import CatalogFeed
from app.models.enums import CatalogFeedType, VerificationStatus
from app.services.catalog import synthetic
from app.services.catalog.gatekeeper import evaluate_feed
from app.services.feeds import fetching, parsing
from app.typing.catalog import GatekeeperResult

logger = structlog.get_logger(__name__)

SessionFactory = Callable[[], Any]


@dataclass(frozen=True)
class VerificationOutcome:
    """Result of polling one catalog feed.

    ``result`` is ``None`` for a not-modified response (keep the existing verdict); ``error`` is
    set when the poll failed and the failure counter should advance.
    """

    result: GatekeeperResult | None = None
    error: str | None = None
    etag: str | None = None
    last_modified: str | None = None


async def verify_catalog_feed(session_factory: SessionFactory, catalog_feed_id: UUID) -> None:
    """Poll one catalog feed and persist the gatekeeper verdict (or a failure)."""
    async with session_factory() as db:
        feed = await feed_crud.get_catalog_feed_by_id(db, feed_id=catalog_feed_id)
        if not feed:
            return
        entity = await entity_crud.get_entity_by_id(db, entity_id=feed.entity_id)
        if not entity:
            return
        feed_url = str(feed.feed_url)
        feed_type = feed.feed_type
        canonical_domain = entity.canonical_domain
        etag = feed.etag_header
        last_modified = feed.last_modified_header

    # Network work happens with no session held.
    if feed_type is CatalogFeedType.SYNTHETIC_HTML:
        outcome = await _evaluate_synthetic(feed_url, canonical_domain)
    else:
        outcome = await _evaluate_native(feed_url, canonical_domain, etag, last_modified)

    async with session_factory() as db:
        feed = await feed_crud.get_catalog_feed_by_id(db, feed_id=catalog_feed_id)
        if not feed:
            return
        if outcome.error:
            await _record_failure(db, feed, outcome.error)
            return
        if outcome.result is not None:
            await feed_crud.apply_verification(db, feed=feed, result=outcome.result)
            feed.failure_count = 0
            feed.etag_header = outcome.etag
            feed.last_modified_header = outcome.last_modified
        feed.next_poll_at = _now() + timedelta(minutes=CATALOG_VERIFY_INTERVAL_MINUTES)
        await db.flush()


async def _evaluate_native(
    feed_url: str, canonical_domain: str, etag: str | None, last_modified: str | None
) -> VerificationOutcome:
    """Fetch/parse a native feed and gate it on host alignment and item link-out ratio."""
    fetch_result = await fetching.fetch_feed_content(feed_url, etag=etag, last_modified=last_modified)
    if fetch_result["error"]:
        return VerificationOutcome(error=fetch_result["error"])
    if fetch_result["status_code"] == 304 or not fetch_result["content"]:
        return VerificationOutcome()  # Unchanged: keep the current verdict.

    final_url = fetch_result.get("final_url") or feed_url
    try:
        parsed = parsing.parse_feed_content(fetch_result["content"], final_url)
    except Exception as exc:  # noqa: BLE001 - a parse failure is recorded as a poll failure
        return VerificationOutcome(error=f"parse error: {exc}")

    result = evaluate_feed(
        canonical_domain=canonical_domain,
        feed_url=final_url,
        item_links=[article.link for article in parsed.articles if article.link],
        redirect_urls=[final_url] if final_url != feed_url else [],
    )
    return VerificationOutcome(
        result=result,
        etag=fetch_result["headers"].get("etag"),
        last_modified=fetch_result["headers"].get("last-modified"),
    )


async def _evaluate_synthetic(feed_url: str, canonical_domain: str) -> VerificationOutcome:
    """Extract a newsroom page and gate it on host alignment and item link-out ratio."""
    html = await fetching.fetch_page_html(feed_url)
    if not html:
        html = await synthetic.render_html_with_browser(feed_url)
    if not html:
        return VerificationOutcome(error="newsroom page fetch failed")

    items = synthetic.extract_news_items(html, feed_url)
    result = evaluate_feed(
        canonical_domain=canonical_domain,
        feed_url=feed_url,
        item_links=[item.url for item in items],
    )
    return VerificationOutcome(result=result)


async def _record_failure(db: Any, feed: CatalogFeed, error: str) -> None:
    """Advance the failure counter, quarantining after the configured threshold."""
    now = _now()
    feed.failure_count = (feed.failure_count or 0) + 1
    feed.last_polled_at = now
    feed.last_updated_at = now
    if feed.failure_count >= CATALOG_MAX_FAILURES:
        feed.verification_status = VerificationStatus.QUARANTINED
        feed.rejection_reason = f"quarantined after {feed.failure_count} failures: {error}"
        feed.next_poll_at = now + timedelta(hours=CATALOG_QUARANTINE_RECHECK_HOURS)
    else:
        backoff = min(2**feed.failure_count * CATALOG_VERIFY_BACKOFF_MINUTES, MAX_ERROR_BACKOFF_MINUTES)
        feed.next_poll_at = now + timedelta(minutes=backoff)
    logger.warning("Catalog feed poll failed", feed_id=str(feed.id), failures=feed.failure_count, error=error)
    await db.flush()


def _now() -> datetime:
    return datetime.now(timezone.utc)
