"""RSS Feed Discovery Router - preview and feed-finding endpoints.

Note: Search functionality has been migrated to Meilisearch with direct frontend integration.
The frontend now uses React InstantSearch to query Meilisearch directly.
"""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.custom_exceptions import ValidationError
from app.core.dependencies import get_current_user
from app.crud.feed.subscription import get_subscription_by_feed_id
from app.db.session import get_db_factory
from app.services.feeds import discovery, fetching, parsing, service
from app.typing.feeds import (
    FeedDiscoveryResponse,
    FeedDiscoveryStep,
    ParsedFeed,
)
from app.typing.user import TokenData
from app.utils.security import validate_url_security
from app.utils.urls import normalize_feed_url

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/discover", tags=["RSS Discovery"])


@router.get("/preview")
async def get_feed_preview(
    *,
    url: str = Query(..., description="RSS feed URL to preview"),
    db_factory=Depends(get_db_factory),
    current_user: TokenData = Depends(get_current_user),
) -> ParsedFeed:
    """
    Get feed metadata from an RSS feed URL for preview purposes.

    Fetches and parses an RSS feed to extract metadata without storing it.
    Also checks if the user is already subscribed to this feed.
    """
    # Reject private/internal targets up front (SSRF)
    try:
        await validate_url_security(url)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL not allowed") from e

    # Fetch feed content
    fetch_result = await fetching.fetch_feed_content(url)
    if fetch_result["error"] or not fetch_result["content"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=fetch_result["error"] or "Could not fetch RSS feed content",
        )

    # Determine canonical URL from fetch result
    final_url = fetch_result.get("final_url") or url
    final_normalized_url = normalize_feed_url(final_url)

    # Parse feed content
    try:
        parsed = parsing.parse_feed_content(fetch_result["content"], final_url)

        # Check if feed exists and if user is subscribed
        async with db_factory() as db:
            existing_feed = await service.feed_crud.get_feed_by_url(db, url=final_normalized_url)
            if existing_feed:
                parsed.id = str(existing_feed.id)
                subscription = await get_subscription_by_feed_id(
                    db, feed_id=existing_feed.id, user_id=UUID(current_user.sub)
                )
                parsed.is_subscribed = subscription is not None

        logger.info(
            "Feed preview generated",
            url=final_normalized_url,
            title=parsed.title,
            is_subscribed=parsed.is_subscribed,
        )
        return parsed
    except Exception as e:
        logger.error("Feed parse failed", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse feed",
        ) from e


@router.get("/find")
async def find_feeds(
    *,
    url: str = Query(..., description="Website or feed URL to search for feeds"),
    db_factory: Any = Depends(get_db_factory),
    current_user: TokenData = Depends(get_current_user),
) -> FeedDiscoveryResponse:
    """
    Find the feeds a website publishes, for a URL pasted into Discover.

    The URL is first tried as a feed. When that fails, the discovery ladder runs (page and parent
    page feed declarations, outbound links, sitemap, well-known suffixes, blog platform hints and
    third-party feed hosts) until a verified feed turns up. Every strategy that was attempted is
    reported so the UI can show what was searched.
    """
    input_url = discovery.normalize_input_url(url)
    try:
        await validate_url_security(input_url)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL not allowed") from e

    report = await discovery.discover_feeds_for_url(input_url)
    feeds = await _build_feed_previews(report, db_factory, UUID(current_user.sub))
    return FeedDiscoveryResponse(
        input_url=report.input_url,
        base_url=report.base_url,
        is_direct_feed=report.is_direct_feed,
        feeds=feeds,
        steps=[
            FeedDiscoveryStep(key=step.key.value, label=step.label, status=step.status.value, found=step.found)
            for step in report.steps
        ],
    )


async def _build_feed_previews(
    report: discovery.FeedDiscoveryReport,
    db_factory: Any,
    user_id: UUID,
) -> list[ParsedFeed]:
    """Parse discovered feeds into preview payloads, annotating existing subscriptions."""
    feeds: list[ParsedFeed] = []
    async with db_factory() as db:
        for candidate in report.candidates:
            normalized_url = normalize_feed_url(candidate.url)
            try:
                parsed = parsing.parse_feed_content(candidate.content, candidate.url)
            except Exception as exc:  # noqa: BLE001 - a feed that will not parse is not offerable
                logger.warning("Discovered feed failed to parse", url=candidate.url, error=str(exc))
                continue

            # Discovery only needs feed identity, so entries are dropped to keep the payload small.
            parsed.articles = []
            parsed.url = normalized_url
            if not parsed.title:
                parsed.title = candidate.title or normalized_url

            existing_feed = await service.feed_crud.get_feed_by_url(db, url=normalized_url)
            if existing_feed:
                parsed.id = str(existing_feed.id)
                subscription = await get_subscription_by_feed_id(
                    db, feed_id=UUID(str(existing_feed.id)), user_id=user_id
                )
                parsed.is_subscribed = subscription is not None
            feeds.append(parsed)

    logger.info(
        "Feed discovery previews built",
        url=report.input_url,
        found=len(report.candidates),
        previews=len(feeds),
    )
    return feeds
