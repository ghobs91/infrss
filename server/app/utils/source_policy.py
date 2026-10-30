"""Editorial source policy: domains that must never be ingested into the catalog.

The catalog owner maintains a blocklist of sources excluded regardless of how they would
otherwise qualify as primary sources — enforced at entity creation, so connectors, autodiscovery
and curated seeds all honour it. Matching is by registrable host, so subdomains are blocked too.

Add a domain here to exclude it everywhere; it is checked before any entity is created.
"""

from __future__ import annotations

# Pro-Israel / Zionist advocacy organisations — excluded by policy, never ingested.
BLOCKED_SOURCE_DOMAINS: frozenset[str] = frozenset(
    {
        "adl.org",  # Anti-Defamation League
        "aipac.org",  # American Israel Public Affairs Committee
        "standwithus.com",
        "camera.org",  # Committee for Accuracy in Middle East Reporting
        "honestreporting.org",
        "zoa.org",  # Zionist Organization of America
    }
)


def is_blocked_source(domain: str) -> bool:
    """True when ``domain`` (or one of its parent domains) is on the editorial blocklist."""
    host = (domain or "").strip().lower().rstrip(".")
    if not host:
        return False
    return any(host == blocked or host.endswith(f".{blocked}") for blocked in BLOCKED_SOURCE_DOMAINS)
