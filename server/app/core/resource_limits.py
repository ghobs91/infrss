"""Resource limits configuration for different user roles.

The paywall has been removed: every role now has unlimited access to every feature.
``-1`` means unlimited and ``True`` means the feature is enabled. The per-role structure is
kept so the ``/users/limits`` response shape stays stable for existing clients.
"""

# Codex Digest allowance.
#
# The generation cap used to be a ROLLING WINDOW keyed on the server clock, with a smaller
# Basic allowance and a larger Pro one. With the paywall removed there is no cap at all, so
# only the window length remains - it still decides when a digest stops being "today's" edition.
CODEX_QUOTA_WINDOW_HOURS = 22

# Every role gets unlimited access now that the paywall is removed.
UNLIMITED_RESOURCE_LIMITS = {
    "max_subscriptions": -1,
    "max_newsletters": -1,
    "max_daily_ai_calls": -1,
    "max_daily_scrapes": -1,
    "semantic_search": True,
    "max_saved_articles": -1,
}

RESOURCE_LIMITS = {
    "basic": dict(UNLIMITED_RESOURCE_LIMITS),
    "pro": dict(UNLIMITED_RESOURCE_LIMITS),
    "admin": dict(UNLIMITED_RESOURCE_LIMITS),
}
