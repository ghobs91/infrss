"""Single feed import worker operations."""

import asyncio
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.exc import InterfaceError, OperationalError

from app.services.feeds.service import add_feed
from app.services.folder import ensure_default_folder
from app.typing.common import ImportStatus
from app.typing.opml import FeedImportError
from app.workers.common import worker_db_factory
from app.workers.opml.progress import OpmlImportTracker

logger = structlog.get_logger(__name__)

# Supavisor/Postgres reject *the client* when the pooler's client cap is hit. That is transient
# (too many concurrent imports), so the import is retried in-task rather than via taskiq's
# retry_on_error: the OPML tracker counts a feed once through mark_success/mark_failure, and a
# taskiq-level retry would mark it both failed and successful. Matched case-insensitively.
_RETRYABLE_DB_MESSAGES = (
    "max client connections",
    "too many clients",
    "remaining connection slots",
    "connection refused",
    "connection was closed",
    "connection reset",
    "server closed the connection",
    "pool timeout",
)

_IMPORT_MAX_ATTEMPTS = 3
_IMPORT_RETRY_BACKOFF_SECONDS = 2.0


def is_retryable_db_error(exc: BaseException) -> bool:
    """True when ``exc`` is a transient database/connection-pool failure worth retrying."""
    if isinstance(exc, (OperationalError, InterfaceError)):
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _RETRYABLE_DB_MESSAGES)


async def import_single_feed(
    user_id: UUID,
    feed_url: str,
    folder_id: str,
    tag_names: list[str] | None = None,
    feed_title: str | None = None,
    update_existing: bool = False,
    parent_task_id: str | None = None,
) -> dict[str, Any]:
    """Execute import logic for a single feed, retrying transient database errors."""
    logger.info("Importing feed", user_id=str(user_id), url=feed_url)

    for attempt in range(1, _IMPORT_MAX_ATTEMPTS + 1):
        try:
            return await _attempt_feed_import(
                user_id=user_id,
                feed_url=feed_url,
                folder_id=folder_id,
                feed_title=feed_title,
                parent_task_id=parent_task_id,
            )
        except Exception as exc:
            if is_retryable_db_error(exc) and attempt < _IMPORT_MAX_ATTEMPTS:
                logger.warning(
                    "Retryable database error during feed import",
                    url=feed_url,
                    attempt=attempt,
                    error=str(exc),
                )
                await asyncio.sleep(_IMPORT_RETRY_BACKOFF_SECONDS * attempt)
                continue
            return await _record_import_failure(parent_task_id, feed_url, feed_title, exc)

    # Unreachable: the loop returns on success or in _record_import_failure.
    raise AssertionError("import retry loop exited without a result")


async def _attempt_feed_import(
    user_id: UUID,
    feed_url: str,
    folder_id: str,
    feed_title: str | None,
    parent_task_id: str | None,
) -> dict[str, Any]:
    """One attempt at importing a feed. Raises on any failure."""
    # Resolve folder
    if folder_id:
        resolved_folder_id = UUID(folder_id)
    else:
        async with worker_db_factory() as db:
            default_folder = await ensure_default_folder(db, user_id=user_id)
            resolved_folder_id = default_folder.id

    # Service Call (Manages its own sessions via factory)
    subscription, created = await add_feed(
        session_factory=worker_db_factory,
        user_id=user_id,
        url=feed_url,
        folder_id=resolved_folder_id,
        custom_title=feed_title,
    )

    if parent_task_id:
        await OpmlImportTracker(parent_task_id).mark_success(already_exists=not created)

    return {
        "success": True,
        "url": feed_url,
        "title": subscription.custom_title or subscription.feed.title,
        "status": (ImportStatus.COMPLETED.value if created else "already_exists"),
    }


async def _record_import_failure(
    parent_task_id: str | None,
    feed_url: str,
    feed_title: str | None,
    exc: BaseException,
) -> dict[str, Any]:
    """Record a single permanent failure for the feed (called once, after retries are exhausted)."""
    error_msg = str(exc)

    if parent_task_id:
        tracker = OpmlImportTracker(parent_task_id)
        await tracker.mark_failure(
            FeedImportError(
                url=feed_url,
                title=feed_title or "Unknown",
                error=error_msg,
                status="failed",
            )
        )

    logger.error("Feed import failed", url=feed_url, error=error_msg)

    return {
        "success": False,
        "url": feed_url,
        "title": feed_title or "Unknown",
        "status": ImportStatus.FAILED.value,
        "error": error_msg,
    }
