"""Shared helpers for primary-source connectors.

Connectors talk to fixed, trusted registries (SEC EDGAR, Federal Register, Wikidata), so unlike
feed fetching they do not run the user-URL SSRF guard; requests are still bounded by timeout.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import aiohttp
import structlog

from app.core.constants import BROWSER_USER_AGENT, CATALOG_CONNECTOR_TIMEOUT
from app.models.enums import EntityType

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class EntitySeed:
    """A primary entity discovered by a connector, ready to upsert."""

    name: str
    entity_type: EntityType
    canonical_domain: str
    cik: str | None = None
    jurisdiction: str | None = None
    newsroom_url: str | None = None


class RateLimiter:
    """Single-process async rate limiter enforcing a minimum interval between acquisitions."""

    def __init__(self, rate_per_sec: float) -> None:
        if rate_per_sec <= 0:
            raise ValueError("rate_per_sec must be positive")
        self._min_interval = 1.0 / rate_per_sec
        self._lock = asyncio.Lock()
        self._last: float = 0.0

    async def acquire(self) -> None:
        """Wait until the next request is permitted by the configured rate."""
        async with self._lock:
            wait = self._min_interval - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


async def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = CATALOG_CONNECTOR_TIMEOUT,
) -> Any:
    """GET and decode a JSON document from a trusted connector endpoint."""
    merged = {"Accept": "application/json", "User-Agent": BROWSER_USER_AGENT}
    if headers:
        merged.update(headers)

    timeout_config = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_config) as session:
        async with session.get(url, headers=merged) as response:
            response.raise_for_status()
            return await response.json(content_type=None)
