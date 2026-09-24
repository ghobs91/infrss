"""Unit tests for the pure plan-compliance computation (no database).

The paywall has been removed, so every role reports unlimited holdings and never requires a
downgrade.
"""

import pytest

from app.core.resource_limits import RESOURCE_LIMITS
from app.services.user.resource_limits import compute_over_limit_state

pytestmark = pytest.mark.unit


def test_resource_limits_are_unlimited_for_every_role() -> None:
    for role in ("basic", "pro", "admin"):
        limits = RESOURCE_LIMITS[role]
        assert limits["max_subscriptions"] == -1
        assert limits["max_newsletters"] == -1
        assert limits["max_daily_ai_calls"] == -1
        assert limits["max_daily_scrapes"] == -1
        assert limits["max_saved_articles"] == -1
        assert limits["semantic_search"] is True


@pytest.mark.parametrize("role", ["BASIC", "PRO", "UserRole.PRO", "ADMIN"])
@pytest.mark.parametrize("holdings", [0, 10, 1000, 5000])
def test_every_role_is_unlimited_and_never_over_limit(role: str, holdings: int) -> None:
    state = compute_over_limit_state(
        role, subscriptions=holdings, newsletters=holdings, saved_articles=holdings
    )

    assert state.subscriptions.limit == -1
    assert state.newsletters.limit == -1
    assert state.saved_articles.limit == -1
    assert state.subscriptions.over is False
    assert state.newsletters.over is False
    assert state.saved_articles.over is False
    assert state.downgrade_required is False
