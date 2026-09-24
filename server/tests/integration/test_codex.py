"""Integration tests for the Codex Digest router, quota enforcement, and pipeline.

Follows the OPML test pattern: monkeypatch `.kiq` to run the underlying task function
synchronously against the isolated test DB, so the whole flow is deterministic without a real
Taskiq broker. LLM calls (Gemini) are mocked - these are not meant to hit the real API.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleContent, FeedArticle
from app.models.enums import CodexDigestStatus
from app.models.feed import Feed, FeedSubscription
from app.models.folder import Folder
from app.models.user import Profile
from app.typing.codex import (
    CodexSynthesisOutput,
    CodexTriageOutput,
    CodexWorthReadingItem,
)
from app.workers.codex_tasks import generate_codex_digest_task


async def _seed_article(
    db_session: AsyncSession,
    *,
    feed: Feed,
    title: str,
    link: str,
    published_at: datetime,
) -> FeedArticle:
    content = ArticleContent(
        id=uuid4(),
        content_hash=hashlib.sha256(link.encode()).hexdigest(),
        title=title,
        link=link,
        description=f"Description for {title}",
    )
    db_session.add(content)
    await db_session.flush()

    article = FeedArticle(
        id=uuid4(),
        feed_id=feed.id,
        content_id=content.id,
        guid_hash=hashlib.sha256(link.encode()).hexdigest(),
        published_at=published_at,
    )
    db_session.add(article)
    await db_session.flush()
    return article


async def _seed_feed_and_subscription(db_session: AsyncSession, *, user: Profile, folder: Folder, title: str) -> Feed:
    feed = Feed(
        id=uuid4(),
        url=f"https://example.com/{uuid4().hex[:8]}/feed.xml",
        title=title,
        link=f"https://example.com/{uuid4().hex[:8]}",
        language="en",
        tags=[],
        tags_native=[],
    )
    db_session.add(feed)
    await db_session.flush()

    subscription = FeedSubscription(
        id=uuid4(),
        user_id=user.id,
        feed_id=feed.id,
        folder_id=folder.id,
    )
    db_session.add(subscription)
    await db_session.flush()
    return feed


def _fake_triage_output(article_ids: list[int]) -> CodexTriageOutput:
    return CodexTriageOutput(
        gist="A quiet day with one small story.",
        clusters=[],
        worth_reading_ids=article_ids[:4],
        themes=["Small Story", "Slow news day"],
    )


def _fake_synthesis_output(article_ids: list[int]) -> CodexSynthesisOutput:
    return CodexSynthesisOutput(
        scale_setter="A handful of articles, nothing major.",
        developments=[],
        worth_reading=[CodexWorthReadingItem(article_id=aid, reason="Worth a look.") for aid in article_ids[:4]],
        closing_line="0 developments found - a quiet day.",
    )


@pytest.mark.asyncio
class TestCodexGenerateEndpoint:
    async def test_generate_returns_202_and_pending_row(
        self, async_client: AsyncClient, test_user: Profile, test_folder: Folder, db_session: AsyncSession, monkeypatch
    ):
        """POST /codex/generate enqueues a task and returns a PENDING row immediately."""
        dispatched: list[tuple] = []

        async def fake_kiq(user_id: str, digest_id: str):
            dispatched.append((user_id, digest_id))
            return SimpleNamespace(task_id="fake-task-id")

        monkeypatch.setattr(generate_codex_digest_task, "kiq", fake_kiq, raising=False)

        response = await async_client.post("/api/codex/generate")

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "pending"
        assert body["digest_date"] == datetime.now(timezone.utc).date().isoformat()
        assert len(dispatched) == 1
        assert dispatched[0][0] == str(test_user.id)

    async def test_generate_is_idempotent_same_day(
        self, async_client: AsyncClient, test_user: Profile, db_session: AsyncSession, monkeypatch
    ):
        """A second request the same day returns the existing row instead of enqueueing again."""
        dispatched: list[tuple] = []

        async def fake_kiq(user_id: str, digest_id: str):
            dispatched.append((user_id, digest_id))
            return SimpleNamespace(task_id="fake-task-id")

        monkeypatch.setattr(generate_codex_digest_task, "kiq", fake_kiq, raising=False)

        first = await async_client.post("/api/codex/generate")
        second = await async_client.post("/api/codex/generate")

        assert first.status_code == 202
        assert second.status_code == 202
        assert first.json()["id"] == second.json()["id"]
        # Only the first request should have enqueued a task.
        assert len(dispatched) == 1

    @pytest.mark.parametrize("stale_status", [CodexDigestStatus.SKIPPED, CodexDigestStatus.FAILED])
    async def test_generate_retries_after_skipped_or_failed_same_day(
        self,
        async_client: AsyncClient,
        test_user: Profile,
        db_session: AsyncSession,
        monkeypatch,
        stale_status: CodexDigestStatus,
    ):
        """Retrying the same day after a SKIPPED/FAILED run recycles the latest edition into
        PENDING - it does not spend a fresh per-day slot.

        Regression: `create_pending_digest` used to blindly INSERT, hitting the unique
        constraint and 500ing on "Try again" / "Check again".
        """
        from app.crud import codex as crud_codex

        today = datetime.now(timezone.utc).date()
        stale = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await crud_codex.finalize_digest(
            db_session,
            stale.id,
            stale_status,
            error="boom" if stale_status is CodexDigestStatus.FAILED else None,
        )
        await db_session.commit()

        dispatched: list[tuple] = []

        async def fake_kiq(user_id: str, digest_id: str):
            dispatched.append((user_id, digest_id))
            return SimpleNamespace(task_id="fake-task-id")

        monkeypatch.setattr(generate_codex_digest_task, "kiq", fake_kiq, raising=False)

        response = await async_client.post("/api/codex/generate")

        assert response.status_code == 202
        body = response.json()
        assert body["id"] == str(stale.id)  # same row, recycled
        assert body["status"] == CodexDigestStatus.PENDING.value
        assert body["progress_phase"] is None
        assert body["error"] is None
        assert len(dispatched) == 1

    async def test_generate_recycles_stale_orphaned_in_progress_digest(
        self, async_client: AsyncClient, test_user: Profile, db_session: AsyncSession, monkeypatch
    ):
        """An IN_PROGRESS row orphaned well past the task's own timeout (crashed worker, a
        dev restart mid-task) must not be served back forever as "still generating" - it
        should self-heal to FAILED and then be recycled fresh, exactly like a real
        SKIPPED/FAILED retry: same row, `requested_at` reset to now, one task enqueued.

        Regression: `enforce_codex_quota` used to hand an in-flight row back unconditionally,
        so a stuck task would make every future click of "Generate" re-show that same
        ever-more-stale digest with a timer that never resets.
        """
        from app.core.constants import CODEX_STALE_IN_FLIGHT_MINUTES
        from app.crud import codex as crud_codex
        from app.models.enums import CodexDigestPhase

        today = datetime.now(timezone.utc).date()
        stale = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await crud_codex.mark_in_progress(db_session, stale.id, CodexDigestPhase.TRIAGING)
        await db_session.commit()
        await _backdate_requested_at(db_session, stale.id, hours_ago=(CODEX_STALE_IN_FLIGHT_MINUTES + 1) / 60)
        await db_session.commit()

        dispatched: list[tuple] = []

        async def fake_kiq(user_id: str, digest_id: str):
            dispatched.append((user_id, digest_id))
            return SimpleNamespace(task_id="fake-task-id")

        monkeypatch.setattr(generate_codex_digest_task, "kiq", fake_kiq, raising=False)

        before = datetime.now(timezone.utc)
        response = await async_client.post("/api/codex/generate")

        assert response.status_code == 202
        body = response.json()
        assert body["id"] == str(stale.id)  # same row, recycled
        assert body["status"] == CodexDigestStatus.PENDING.value
        assert body["error"] is None
        # requested_at reset to now, not the 2-hour-old timestamp we backdated it to.
        assert datetime.fromisoformat(body["requested_at"]) >= before
        assert len(dispatched) == 1

    async def test_generate_disabled_when_ai_off(self, async_client: AsyncClient, test_user: Profile, monkeypatch):
        """When ENABLE_AI is False, the endpoint returns a not-entitled response, no enqueue."""
        from app.routers import codex as codex_router_module

        monkeypatch.setattr(codex_router_module, "get_settings", lambda: SimpleNamespace(ENABLE_AI=False))

        response = await async_client.post("/api/codex/generate")

        assert response.status_code == 202
        body = response.json()
        assert body["entitled"] is False
        assert body["error_code"] == "AI_DISABLED"

    async def test_admin_bypasses_quota(
        self, async_admin_client: AsyncClient, admin_user: Profile, db_session: AsyncSession, monkeypatch
    ):
        """ADMIN role is always allowed, regardless of existing digests this month."""
        from app.crud import codex as crud_codex

        today = datetime.now(timezone.utc).date()
        for days_ago in range(1, 6):
            digest_date = today - timedelta(days=days_ago)
            digest = await crud_codex.create_pending_digest(db_session, admin_user.id, digest_date)
            await crud_codex.finalize_digest(db_session, digest.id, CodexDigestStatus.COMPLETED, payload={})
        await db_session.commit()

        async def fake_kiq(user_id: str, digest_id: str):
            return SimpleNamespace(task_id="fake-task-id")

        monkeypatch.setattr(generate_codex_digest_task, "kiq", fake_kiq, raising=False)

        response = await async_admin_client.post("/api/codex/generate")

        assert response.status_code == 202
        assert response.json()["status"] == "pending"


@pytest.mark.asyncio
class TestCodexTodayEndpoint:
    async def test_today_returns_404_when_no_digest(self, async_client: AsyncClient, test_user: Profile):
        response = await async_client.get("/api/codex/today")
        assert response.status_code == 404

    async def test_today_returns_latest_digest(
        self, async_client: AsyncClient, test_user: Profile, db_session: AsyncSession
    ):
        from app.crud import codex as crud_codex

        today = datetime.now(timezone.utc).date()
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await crud_codex.finalize_digest(
            db_session,
            digest.id,
            CodexDigestStatus.COMPLETED,
            payload={
                "gist": "Quiet day.",
                "scale_setter": "Nothing much happened.",
                "developments": [],
                "worth_reading": [],
                "closing_line": "0 developments found.",
            },
        )
        await db_session.commit()

        response = await async_client.get("/api/codex/today")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(digest.id)
        assert body["status"] == "completed"
        assert body["payload"]["gist"] == "Quiet day."

    async def test_today_self_heals_orphaned_in_progress_digest(
        self, async_client: AsyncClient, test_user: Profile, db_session: AsyncSession
    ):
        """An IN_PROGRESS row far past the generation task's own timeout is orphaned - the
        worker crashed, or something (a dev restart, an uncaught cancellation) killed it
        mid-task without ever reaching a terminal status. GET /today should self-heal it to
        FAILED rather than serving it back forever with a `requested_at` that only gets
        staler, which read on the client as a "Building..." screen whose elapsed timer starts
        from however long ago the task actually died.
        """
        from app.core.constants import CODEX_STALE_IN_FLIGHT_MINUTES
        from app.crud import codex as crud_codex
        from app.models.enums import CodexDigestPhase

        today = datetime.now(timezone.utc).date()
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await crud_codex.mark_in_progress(db_session, digest.id, CodexDigestPhase.TRIAGING)
        await db_session.commit()
        await _backdate_requested_at(db_session, digest.id, hours_ago=(CODEX_STALE_IN_FLIGHT_MINUTES + 1) / 60)
        await db_session.commit()

        response = await async_client.get("/api/codex/today")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(digest.id)
        assert body["status"] == "failed"

    async def test_today_leaves_recent_in_progress_digest_alone(
        self, async_client: AsyncClient, test_user: Profile, db_session: AsyncSession
    ):
        """A digest still comfortably inside the task's own timeout is a real in-flight
        generation, not an orphan - it must not be healed away mid-run."""
        from app.crud import codex as crud_codex
        from app.models.enums import CodexDigestPhase

        today = datetime.now(timezone.utc).date()
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await crud_codex.mark_in_progress(db_session, digest.id, CodexDigestPhase.TRIAGING)
        await db_session.commit()

        response = await async_client.get("/api/codex/today")

        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    async def test_today_hides_digest_older_than_window(
        self, async_client: AsyncClient, test_user: Profile, db_session: AsyncSession
    ):
        """A digest requested more than CODEX_QUOTA_WINDOW_HOURS ago is yesterday's news - GET
        /today must 404 so every client falls back to the "Ready to generate?" empty state
        instead of serving a stale edition."""
        from app.core.resource_limits import CODEX_QUOTA_WINDOW_HOURS
        from app.crud import codex as crud_codex

        today = datetime.now(timezone.utc).date()
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await crud_codex.finalize_digest(
            db_session,
            digest.id,
            CodexDigestStatus.COMPLETED,
            payload={
                "gist": "Old.",
                "scale_setter": "Nothing much happened.",
                "developments": [],
                "worth_reading": [],
                "closing_line": "0 developments found.",
            },
        )
        await db_session.commit()
        await _backdate_requested_at(db_session, digest.id, hours_ago=CODEX_QUOTA_WINDOW_HOURS + 0.05)
        await db_session.commit()

        response = await async_client.get("/api/codex/today")

        assert response.status_code == 404

    async def test_today_serves_digest_inside_window_with_expiry(
        self, async_client: AsyncClient, test_user: Profile, db_session: AsyncSession
    ):
        """A digest still inside the window is served, carrying `expires_at` (requested_at +
        CODEX_QUOTA_WINDOW_HOURS) so clients can drop it the moment it ages out."""
        from app.core.resource_limits import CODEX_QUOTA_WINDOW_HOURS
        from app.crud import codex as crud_codex

        today = datetime.now(timezone.utc).date()
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await crud_codex.finalize_digest(
            db_session,
            digest.id,
            CodexDigestStatus.COMPLETED,
            payload={
                "gist": "Fresh.",
                "scale_setter": "Nothing much happened.",
                "developments": [],
                "worth_reading": [],
                "closing_line": "0 developments found.",
            },
        )
        await db_session.commit()
        await _backdate_requested_at(db_session, digest.id, hours_ago=CODEX_QUOTA_WINDOW_HOURS - 0.1)
        await db_session.commit()

        response = await async_client.get("/api/codex/today")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(digest.id)
        requested_at = datetime.fromisoformat(body["requested_at"])
        expires_at = datetime.fromisoformat(body["expires_at"])
        assert expires_at - requested_at == timedelta(hours=CODEX_QUOTA_WINDOW_HOURS)


@pytest.mark.asyncio
class TestCodexPipelineViaTask:
    """Exercise the whole pipeline through the real worker task, LLM calls mocked."""

    async def test_full_pipeline_persists_completed_digest(
        self, test_user: Profile, test_folder: Folder, db_session: AsyncSession, monkeypatch
    ):
        from app.crud import codex as crud_codex

        feed = await _seed_feed_and_subscription(db_session, user=test_user, folder=test_folder, title="Test Feed")
        now = datetime.now(timezone.utc)
        for i in range(5):
            await _seed_article(
                db_session,
                feed=feed,
                title=f"Story {i}",
                link=f"https://example.com/story-{i}",
                published_at=now - timedelta(hours=i),
            )
        await db_session.commit()

        today = now.date()
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await db_session.commit()

        # Mock the LLM calls - integration tests never hit the real Gemini API.
        async def fake_triage(prompt: str) -> CodexTriageOutput:
            return _fake_triage_output([1, 2, 3, 4, 5])

        async def fake_synthesis(prompt: str) -> CodexSynthesisOutput:
            return _fake_synthesis_output([1, 2, 3, 4, 5])

        monkeypatch.setattr("app.services.codex.pipeline.run_codex_triage", fake_triage)
        monkeypatch.setattr("app.services.codex.pipeline.run_codex_synthesis", fake_synthesis)

        # Mock full-text fetch + image probing - no real HTTP calls in integration tests.
        async def fake_fetch_full_texts(items, stored_bodies=None):
            return {item.id: item.description or "" for item in items}

        async def fake_select_imagery(articles):
            from app.services.codex.imagery import DevelopmentImagery

            return DevelopmentImagery()

        monkeypatch.setattr("app.services.codex.pipeline.fetch_full_texts", fake_fetch_full_texts)
        monkeypatch.setattr("app.services.codex.pipeline.select_development_imagery", fake_select_imagery)

        await generate_codex_digest_task(str(test_user.id), str(digest.id))

        await db_session.refresh(digest)
        assert digest.status == CodexDigestStatus.COMPLETED.value
        assert digest.input_article_count == 5
        assert digest.payload is not None
        assert digest.payload["gist"] == "A quiet day with one small story."
        assert len(digest.payload["worth_reading"]) == 4
        assert digest.payload["themes"] == ["Small Story", "Slow news day"]
        # No developments on a quiet day -> nothing was condensed.
        assert digest.payload["stats"] is None
        # article_count / articles-shown alignment regression guard
        for wr in digest.payload["worth_reading"]:
            assert "article" in wr
            assert wr["article"]["title"].startswith("Story")

    async def test_pipeline_skips_with_no_articles(self, test_user: Profile, db_session: AsyncSession, monkeypatch):
        from app.crud import codex as crud_codex

        today = datetime.now(timezone.utc).date()
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, today)
        await db_session.commit()

        await generate_codex_digest_task(str(test_user.id), str(digest.id))

        await db_session.refresh(digest)
        assert digest.status == CodexDigestStatus.SKIPPED.value
        assert digest.input_article_count == 0

    async def test_pipeline_tracks_progress_phase(
        self, test_user: Profile, test_folder: Folder, db_session: AsyncSession, monkeypatch
    ):
        """progress_phase advances through the pipeline and holds its last value at completion."""
        from app.crud import codex as crud_codex

        feed = await _seed_feed_and_subscription(db_session, user=test_user, folder=test_folder, title="Test Feed")
        now = datetime.now(timezone.utc)
        await _seed_article(
            db_session, feed=feed, title="Only Story", link="https://example.com/only", published_at=now
        )
        await db_session.commit()

        digest = await crud_codex.create_pending_digest(db_session, test_user.id, now.date())
        await db_session.commit()

        observed_phases: list[str] = []

        async def fake_triage(prompt: str) -> CodexTriageOutput:
            observed_phases.append((await db_session.get(type(digest), digest.id)).progress_phase)
            return _fake_triage_output([1])

        async def fake_synthesis(prompt: str) -> CodexSynthesisOutput:
            observed_phases.append((await db_session.get(type(digest), digest.id)).progress_phase)
            return _fake_synthesis_output([1])

        async def fake_fetch_full_texts(items, stored_bodies=None):
            observed_phases.append((await db_session.get(type(digest), digest.id)).progress_phase)
            return {item.id: item.description or "" for item in items}

        async def fake_select_imagery(articles):
            from app.services.codex.imagery import DevelopmentImagery

            return DevelopmentImagery()

        monkeypatch.setattr("app.services.codex.pipeline.run_codex_triage", fake_triage)
        monkeypatch.setattr("app.services.codex.pipeline.run_codex_synthesis", fake_synthesis)
        monkeypatch.setattr("app.services.codex.pipeline.fetch_full_texts", fake_fetch_full_texts)
        monkeypatch.setattr("app.services.codex.pipeline.select_development_imagery", fake_select_imagery)

        await generate_codex_digest_task(str(test_user.id), str(digest.id))

        assert observed_phases == ["triaging", "reading", "synthesizing"]

        await db_session.refresh(digest)
        assert digest.status == CodexDigestStatus.COMPLETED.value
        # Phase holds its last value once terminal, per the CodexDigestPhase docstring.
        assert digest.progress_phase == "synthesizing"

    async def test_pipeline_marks_failed_on_generation_error(
        self, test_user: Profile, test_folder: Folder, db_session: AsyncSession, monkeypatch
    ):
        from app.crud import codex as crud_codex
        from app.services.ai.codex import CodexGenerationError

        feed = await _seed_feed_and_subscription(db_session, user=test_user, folder=test_folder, title="Test Feed")
        now = datetime.now(timezone.utc)
        await _seed_article(
            db_session, feed=feed, title="A Story", link="https://example.com/a-story", published_at=now
        )
        await db_session.commit()

        digest = await crud_codex.create_pending_digest(db_session, test_user.id, now.date())
        await db_session.commit()

        async def failing_triage(prompt: str):
            raise CodexGenerationError("Malformed model output")

        monkeypatch.setattr("app.services.codex.pipeline.run_codex_triage", failing_triage)

        await generate_codex_digest_task(str(test_user.id), str(digest.id))

        await db_session.refresh(digest)
        assert digest.status == CodexDigestStatus.FAILED.value
        assert digest.error == "Malformed model output"


@pytest.mark.asyncio
class TestCodexPreferencesEndpoint:
    async def test_get_preferences_defaults_to_empty(self, async_client: AsyncClient, test_user: Profile):
        """A user who has never saved preferences gets an empty excluded set."""
        response = await async_client.get("/api/codex/preferences")
        assert response.status_code == 200
        assert response.json() == {"excluded_folder_ids": []}

    async def test_put_preferences_round_trips(
        self, async_client: AsyncClient, test_user: Profile, test_folder: Folder
    ):
        """PUT stores the excluded folder ids; a subsequent GET reads them back."""
        put = await async_client.put(
            "/api/codex/preferences",
            json={"excluded_folder_ids": [str(test_folder.id)]},
        )
        assert put.status_code == 200
        assert put.json()["excluded_folder_ids"] == [str(test_folder.id)]

        get = await async_client.get("/api/codex/preferences")
        assert get.json()["excluded_folder_ids"] == [str(test_folder.id)]

        # Clearing it works too.
        cleared = await async_client.put("/api/codex/preferences", json={"excluded_folder_ids": []})
        assert cleared.json()["excluded_folder_ids"] == []

    async def test_put_preferences_rejects_foreign_folder(
        self, async_client: AsyncClient, test_user: Profile, admin_user: Profile, db_session: AsyncSession
    ):
        """A folder id that doesn't belong to the caller is refused with a 4xx."""
        from app.models.folder import Folder as FolderModel

        other = FolderModel(id=uuid4(), user_id=admin_user.id, name="Someone else's folder")
        db_session.add(other)
        await db_session.commit()

        response = await async_client.put(
            "/api/codex/preferences",
            json={"excluded_folder_ids": [str(other.id)]},
        )
        assert response.status_code >= 400
        assert response.json()["error_code"] == "CODEX_UNKNOWN_FOLDER"


@pytest.mark.asyncio
class TestCodexPipelineRespectsPreferences:
    async def test_excluded_folder_articles_are_omitted(
        self, test_user: Profile, db_session: AsyncSession, monkeypatch
    ):
        """Articles from feeds in an excluded folder never reach the digest catalog."""
        from app.crud import codex as crud_codex

        included_folder = Folder(id=uuid4(), user_id=test_user.id, name="Included")
        excluded_folder = Folder(id=uuid4(), user_id=test_user.id, name="Excluded")
        db_session.add_all([included_folder, excluded_folder])
        await db_session.flush()

        included_feed = await _seed_feed_and_subscription(
            db_session, user=test_user, folder=included_folder, title="Included Feed"
        )
        excluded_feed = await _seed_feed_and_subscription(
            db_session, user=test_user, folder=excluded_folder, title="Excluded Feed"
        )
        now = datetime.now(timezone.utc)
        for i in range(3):
            await _seed_article(
                db_session,
                feed=included_feed,
                title=f"Kept {i}",
                link=f"https://example.com/kept-{i}",
                published_at=now - timedelta(hours=i),
            )
            await _seed_article(
                db_session,
                feed=excluded_feed,
                title=f"Dropped {i}",
                link=f"https://example.com/dropped-{i}",
                published_at=now - timedelta(hours=i),
            )

        await crud_codex.upsert_preferences(db_session, test_user.id, excluded_folder_ids=[excluded_folder.id])
        digest = await crud_codex.create_pending_digest(db_session, test_user.id, now.date())
        await db_session.commit()

        seen_titles: list[str] = []

        async def fake_triage(prompt: str) -> CodexTriageOutput:
            seen_titles.append(prompt)
            return _fake_triage_output([1, 2, 3])

        async def fake_synthesis(prompt: str) -> CodexSynthesisOutput:
            return _fake_synthesis_output([1, 2, 3])

        async def fake_fetch_full_texts(items, stored_bodies=None):
            return {item.id: item.description or "" for item in items}

        async def fake_select_imagery(articles):
            from app.services.codex.imagery import DevelopmentImagery

            return DevelopmentImagery()

        monkeypatch.setattr("app.services.codex.pipeline.run_codex_triage", fake_triage)
        monkeypatch.setattr("app.services.codex.pipeline.run_codex_synthesis", fake_synthesis)
        monkeypatch.setattr("app.services.codex.pipeline.fetch_full_texts", fake_fetch_full_texts)
        monkeypatch.setattr("app.services.codex.pipeline.select_development_imagery", fake_select_imagery)

        await generate_codex_digest_task(str(test_user.id), str(digest.id))

        await db_session.refresh(digest)
        assert digest.status == CodexDigestStatus.COMPLETED.value
        # Only the 3 included-folder articles from a single source made the catalog.
        assert digest.input_article_count == 3
        assert digest.input_source_count == 1
        triage_prompt = seen_titles[0]
        assert "Kept 0" in triage_prompt
        assert "Dropped 0" not in triage_prompt


class TestResolveLocalDate:
    """The router's ±1-day clamp on the client-supplied local calendar day. It's a display
    label only (``digest_date``) - a real timezone is at most UTC±14h so legit values pass
    straight through and only a spoof gets clamped. It never affects the quota."""

    def test_none_body_falls_back_to_utc_today(self):
        from app.routers.codex import _resolve_local_date

        assert _resolve_local_date(None) == datetime.now(timezone.utc).date()

    def test_missing_local_date_falls_back_to_utc_today(self):
        from app.routers.codex import _resolve_local_date
        from app.typing.codex import CodexGenerateRequest

        assert _resolve_local_date(CodexGenerateRequest()) == datetime.now(timezone.utc).date()

    @pytest.mark.parametrize("offset_days", [-1, 0, 1])
    def test_within_one_day_passes_through_unchanged(self, offset_days: int):
        from app.routers.codex import _resolve_local_date
        from app.typing.codex import CodexGenerateRequest

        supplied = datetime.now(timezone.utc).date() + timedelta(days=offset_days)
        assert _resolve_local_date(CodexGenerateRequest(local_date=supplied)) == supplied

    def test_far_future_is_clamped_to_utc_tomorrow(self):
        from app.routers.codex import _resolve_local_date
        from app.typing.codex import CodexGenerateRequest

        utc_today = datetime.now(timezone.utc).date()
        supplied = utc_today + timedelta(days=30)
        assert _resolve_local_date(CodexGenerateRequest(local_date=supplied)) == utc_today + timedelta(days=1)

    def test_far_past_is_clamped_to_utc_yesterday(self):
        from app.routers.codex import _resolve_local_date
        from app.typing.codex import CodexGenerateRequest

        utc_today = datetime.now(timezone.utc).date()
        supplied = utc_today - timedelta(days=30)
        assert _resolve_local_date(CodexGenerateRequest(local_date=supplied)) == utc_today - timedelta(days=1)


async def _backdate_requested_at(db: AsyncSession, digest_id, *, hours_ago: float) -> None:
    """Push a digest's requested_at into the past so it sits outside the rolling quota window."""
    from app.models.codex import CodexDigest

    row = await db.get(CodexDigest, digest_id)
    assert row is not None
    row.requested_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    await db.flush()

