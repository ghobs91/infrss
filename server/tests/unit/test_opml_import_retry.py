"""Unit tests for OPML single-feed import retry behavior (no DB, no network)."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from app.workers.opml import import_feed
from app.workers.opml.import_feed import is_retryable_db_error


@pytest.mark.unit
def test_retryable_on_supavisor_client_limit_message():
    assert is_retryable_db_error(RuntimeError("Max client connections reached")) is True


@pytest.mark.unit
def test_retryable_on_sqlalchemy_operational_error():
    exc = OperationalError("SELECT 1", {}, Exception("connection reset"))
    assert is_retryable_db_error(exc) is True


@pytest.mark.unit
def test_not_retryable_on_permanent_error():
    assert is_retryable_db_error(ValueError("Failed to parse feed")) is False


class _FakeTracker:
    """Captures mark_success/mark_failure across instances (the code builds one per call)."""

    successes: list[bool] = []
    failures: list = []

    def __init__(self, task_id: str):
        self.task_id = task_id

    async def mark_success(self, already_exists: bool = False) -> None:
        _FakeTracker.successes.append(already_exists)

    async def mark_failure(self, error) -> None:
        _FakeTracker.failures.append(error)


def _patch(monkeypatch) -> None:
    _FakeTracker.successes = []
    _FakeTracker.failures = []
    monkeypatch.setattr(import_feed, "OpmlImportTracker", _FakeTracker)
    monkeypatch.setattr(import_feed, "_IMPORT_RETRY_BACKOFF_SECONDS", 0)


def _subscription() -> SimpleNamespace:
    return SimpleNamespace(custom_title="Feed", feed=SimpleNamespace(title="Feed"))


@pytest.mark.asyncio
@pytest.mark.unit
async def test_retries_then_succeeds_without_double_counting(monkeypatch):
    _patch(monkeypatch)
    calls = {"n": 0}

    async def flaky(**_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("Max client connections reached")
        return _subscription(), True

    monkeypatch.setattr(import_feed, "add_feed", flaky)

    result = await import_feed.import_single_feed(
        user_id=uuid4(),
        feed_url="https://example.com/feed",
        folder_id=str(uuid4()),
        parent_task_id="t",
    )

    assert result["success"] is True
    assert calls["n"] == 2
    assert _FakeTracker.successes == [False]
    assert _FakeTracker.failures == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_exhausts_retries_then_records_one_failure(monkeypatch):
    _patch(monkeypatch)
    calls = {"n": 0}

    async def always_fails(**_kwargs):
        calls["n"] += 1
        raise RuntimeError("Max client connections reached")

    monkeypatch.setattr(import_feed, "add_feed", always_fails)

    result = await import_feed.import_single_feed(
        user_id=uuid4(),
        feed_url="https://example.com/feed",
        folder_id=str(uuid4()),
        parent_task_id="t",
    )

    assert result["success"] is False
    assert calls["n"] == import_feed._IMPORT_MAX_ATTEMPTS
    assert len(_FakeTracker.failures) == 1
    assert _FakeTracker.successes == []


@pytest.mark.asyncio
@pytest.mark.unit
async def test_permanent_error_is_not_retried(monkeypatch):
    _patch(monkeypatch)
    calls = {"n": 0}

    async def permanent(**_kwargs):
        calls["n"] += 1
        raise ValueError("Failed to parse feed")

    monkeypatch.setattr(import_feed, "add_feed", permanent)

    result = await import_feed.import_single_feed(
        user_id=uuid4(),
        feed_url="https://example.com/feed",
        folder_id=str(uuid4()),
        parent_task_id="t",
    )

    assert result["success"] is False
    assert calls["n"] == 1
    assert len(_FakeTracker.failures) == 1
