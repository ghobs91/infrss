"""
Resource limit enforcement logic.
"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis_cache
from app.core.constants import NEWSLETTER_LIMIT_ERROR_CODE, SCRAPE_USAGE_KEY_PREFIX, USAGE_COUNTER_TTL_SECONDS
from app.core.custom_exceptions import NotFoundError, ResourceLimitError
from app.core.resource_limits import RESOURCE_LIMITS
from app.crud import codex as crud_codex
from app.crud.profile import get_current_usage, get_profile_by_id
from app.models.codex import CodexDigest
from app.typing.user import OverLimitResource, OverLimitState


def _get_limit_for_role(role: str, resource: str) -> Any:
    """Get the limit for a specific role and resource."""
    # Normalize role (handle "UserRole.BASIC" vs "basic")
    normalized_role = role.lower().split(".")[-1]

    role_limits = RESOURCE_LIMITS.get(normalized_role, RESOURCE_LIMITS["basic"])
    return role_limits.get(resource, 0)


def _over_limit_resource(usage: int, limit: int) -> OverLimitResource:
    """Usage vs. limit for one resource; -1 means unlimited and is never over."""
    return OverLimitResource(usage=usage, limit=limit, over=limit != -1 and usage > limit)


def compute_over_limit_state(role: str, subscriptions: int, newsletters: int, saved_articles: int) -> OverLimitState:
    """
    Compare what a user currently holds against their role's limits.

    The paywall has been removed, so every role's limits are unlimited and this always reports
    no overage. Kept so the ``/users/limits`` response shape and the (dormant) downgrade flow
    still work.
    """
    subs = _over_limit_resource(subscriptions, _get_limit_for_role(role, "max_subscriptions"))
    news = _over_limit_resource(newsletters, _get_limit_for_role(role, "max_newsletters"))
    saved = _over_limit_resource(saved_articles, _get_limit_for_role(role, "max_saved_articles"))
    return OverLimitState(
        downgrade_required=role.lower().split(".")[-1] not in {"pro", "admin"} and (subs.over or news.over),
        subscriptions=subs,
        newsletters=news,
        saved_articles=saved,
    )


async def get_over_limit_state(db: AsyncSession, user_id: UUID) -> OverLimitState:
    """Load the user's role and holdings and compute their over-limit state."""
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    return compute_over_limit_state(
        str(profile.role),
        subscriptions=await get_current_usage(db, user_id, "max_subscriptions"),
        newsletters=await get_current_usage(db, user_id, "max_newsletters"),
        saved_articles=await get_current_usage(db, user_id, "max_saved_articles"),
    )


async def enforce_subscription_limit(db: AsyncSession, user_id: UUID, additional_count: int = 1) -> None:
    """
    Checks subscription limit and raises ResourceLimitError if exceeded.
    """
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    resource = "max_subscriptions"
    user_role = str(profile.role)

    limit = _get_limit_for_role(user_role, resource)

    # Check limit
    if limit != -1:
        current = await get_current_usage(db, user_id, resource)
        if current + additional_count > limit:
            raise ResourceLimitError(
                message="Subscription limit would be exceeded. Please upgrade your plan.",
                error_code="SUBSCRIPTION_LIMIT_EXCEEDED",
                details={
                    "current_usage": current,
                    "requested_additional": additional_count,
                    "limit": limit,
                    "would_be_total": current + additional_count,
                },
            )


async def enforce_newsletter_limit(db: AsyncSession, user_id: UUID, additional_count: int = 1) -> None:
    """
    Check the newsletter cap before adding a NEW newsletter subscription.

    Only call this when the user is not already subscribed to the sender - emails from an
    existing newsletter must keep flowing at the cap.

    Raises:
        ResourceLimitError: When the new subscription would push the user over the cap.
    """
    # Newsletters also consume the total subscription allowance.
    await enforce_subscription_limit(db, user_id, additional_count)
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    resource = "max_newsletters"
    limit = _get_limit_for_role(str(profile.role), resource)
    if limit == -1:
        return

    current = await get_current_usage(db, user_id, resource)
    if current + additional_count > limit:
        raise ResourceLimitError(
            message=f"You've reached the limit of {limit} newsletters. Unsubscribe from one to add another.",
            error_code=NEWSLETTER_LIMIT_ERROR_CODE,
            details={"current_usage": current, "requested_additional": additional_count, "limit": limit},
        )


async def enforce_saved_articles_limit(db: AsyncSession, user_id: UUID) -> None:
    """
    Check the saved (read-later) article cap before a NEW save.

    Only call this when an article is transitioning from unsaved to saved - re-saving an
    already-saved article (e.g. updating its note) must not be blocked at the cap.

    Raises:
        ResourceLimitError: When the user already holds the maximum number of saved articles.
    """
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    resource = "max_saved_articles"
    limit = _get_limit_for_role(str(profile.role), resource)
    if limit == -1:
        return

    current = await get_current_usage(db, user_id, resource)
    if current >= limit:
        raise ResourceLimitError(
            message=(
                f"You've saved {limit} articles, the most the free plan allows. "
                "Remove a saved article or upgrade to Pro for unlimited saves."
            ),
            error_code="SAVED_ARTICLES_LIMIT_EXCEEDED",
            details={"current_usage": current, "limit": limit},
        )


async def enforce_daily_ai_limit(db: AsyncSession, user_id: UUID) -> None:
    """
    Checks and speculatively increments daily AI invocation limit.
    Raises ResourceLimitError if daily limit exceeded.
    """
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    user_role = str(profile.role)
    limit = _get_limit_for_role(user_role, "max_daily_ai_calls")

    if limit == -1:
        # Unlimited for every role now that the paywall is removed
        return

    today_str = date.today().isoformat()
    redis_key = f"ai_usage:{user_id}:{today_str}"

    # Speculatively increment
    # TTL of 36 hours is safe for timezone changes
    current = await redis_cache.incr(redis_key, ttl_seconds=36 * 3600)

    if current > limit:
        # Revert speculative increment
        await redis_cache.decr(redis_key)
        raise ResourceLimitError(
            message=f"Daily AI invocation limit of {limit} reached. Please upgrade to Pro for 100 calls per day.",
            error_code="AI_LIMIT_EXCEEDED",
            details={
                "current_usage": current - 1,
                "limit": limit,
            },
        )


def _scrape_usage_key(user_id: UUID) -> str:
    """Redis key for a user's article-scrape counter for the current UTC day."""
    return f"{SCRAPE_USAGE_KEY_PREFIX}:{user_id}:{date.today().isoformat()}"


async def check_daily_scrape_limit(db: AsyncSession, user_id: UUID) -> bool:
    """
    Check the daily article-scrape quota and speculatively increment it.

    Returns True if a scrape is allowed (and the counter has been incremented),
    False if the daily limit is already reached (counter left unchanged).

    This is the single place holding the scrape counter logic; callers that need
    a hard failure use ``enforce_daily_scrape_limit``.
    """
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    limit = _get_limit_for_role(str(profile.role), "max_daily_scrapes")

    if limit == -1:
        # Unlimited for every role now that the paywall is removed
        return True

    redis_key = _scrape_usage_key(user_id)
    current = await redis_cache.incr(redis_key, ttl_seconds=USAGE_COUNTER_TTL_SECONDS)

    if current > limit:
        # Revert speculative increment
        await redis_cache.decr(redis_key)
        return False

    return True


async def enforce_daily_scrape_limit(db: AsyncSession, user_id: UUID) -> None:
    """
    Speculatively increment the daily scrape counter, raising ResourceLimitError
    if the limit is exceeded. Used by the explicit full-text extraction endpoint.
    """
    if await check_daily_scrape_limit(db, user_id):
        return

    profile = await get_profile_by_id(db, user_id=user_id)
    limit = _get_limit_for_role(str(profile.role), "max_daily_scrapes") if profile else 0
    raise ResourceLimitError(
        message=f"Daily article extraction limit of {limit} reached. Upgrade to Pro for unlimited extractions.",
        error_code="SCRAPE_LIMIT_EXCEEDED",
        details={"limit": limit},
    )


async def enforce_codex_quota(db: AsyncSession, user_id: UUID, local_date: date | None = None) -> CodexDigest | None:
    """Decide whether the user may start a new Codex digest generation right now.

    The paywall has been removed, so there is no per-role generation cap - every user is
    unlimited. Returns:
      - an existing CodexDigest row -> serve it back so the client keeps polling an in-flight
        generation instead of starting a duplicate;
      - None                       -> the caller should create the next PENDING digest.

    A SKIPPED / FAILED latest generation is always retryable in place. ``local_date`` is
    accepted for backwards compatibility and plays no part.
    """
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    # A retryable (SKIPPED/FAILED) most-recent generation is re-run in place.
    if await crud_codex.get_latest_retryable(db, user_id) is not None:
        return None

    # Hand an in-flight generation back so the client keeps polling it (no duplicate).
    in_flight = await crud_codex.get_latest_in_flight(db, user_id)
    if in_flight is not None:
        return in_flight

    return None


async def get_user_limits_and_usage(db: AsyncSession, user_id: UUID, local_date: date | None = None) -> dict[str, Any]:
    """
    Get user limits configuration and current usage stats.

    ``local_date`` is accepted for backwards compatibility but plays no part.
    """
    profile = await get_profile_by_id(db, user_id=user_id)
    if not profile:
        raise NotFoundError(message="User profile not found", error_code="USER_PROFILE_NOT_FOUND")

    user_role = str(profile.role)
    role_lower = user_role.lower().split(".")[-1]

    limits = RESOURCE_LIMITS.get(role_lower, RESOURCE_LIMITS["basic"])

    # Get current usages
    sub_usage = await get_current_usage(db, user_id, "max_subscriptions")
    saved_usage = await get_current_usage(db, user_id, "max_saved_articles")
    newsletter_usage = await get_current_usage(db, user_id, "max_newsletters")

    today_str = date.today().isoformat()
    ai_usage_str = await redis_cache.get(f"ai_usage:{user_id}:{today_str}")
    ai_usage = int(ai_usage_str) if ai_usage_str else 0

    scrape_usage_str = await redis_cache.get(_scrape_usage_key(user_id))
    scrape_usage = int(scrape_usage_str) if scrape_usage_str else 0

    codex_usage = await _get_codex_usage(db, user_id, role_lower, local_date)
    over_limit = compute_over_limit_state(user_role, sub_usage, newsletter_usage, saved_usage)

    return {
        "role": profile.role,
        "limits": {**limits, "codex": {}},
        "usage": {
            "subscriptions": sub_usage,
            "saved_articles": saved_usage,
            "newsletters": newsletter_usage,
            "daily_ai_calls": ai_usage,
            "daily_scrapes": scrape_usage,
            "codex": codex_usage,
        },
        "over_limit": over_limit,
    }


async def _get_codex_usage(
    db: AsyncSession, user_id: UUID, role_lower: str, local_date: date | None = None
) -> dict[str, Any]:
    """Build the Codex usage summary shown in /users/limits.

    The paywall has been removed, so every role is unlimited. The arguments are kept for
    backwards compatibility and play no part.
    """
    return {"unlimited": True}
