"""Catalog connector sync operations (SEC, Federal Register, Wikidata)."""

import structlog

from app.core.config import get_settings
from app.services.catalog.connectors import federal_register, sec, wikidata
from app.services.catalog.connectors.base import RateLimiter
from app.workers.common import worker_db_factory

logger = structlog.get_logger(__name__)


async def sync_sec_ciks() -> dict[str, int]:
    """Fetch the SEC ticker map and attach CIKs to matching entities."""
    settings = get_settings()
    limiter = RateLimiter(settings.SEC_RATE_LIMIT_RPS)
    payload = await sec.fetch_company_tickers(settings.SEC_USER_AGENT, limiter)
    companies = sec.parse_company_tickers(payload)
    async with worker_db_factory() as db:
        updated = await sec.apply_ciks_to_entities(db, companies)
    return {"companies": len(companies), "updated": updated}


async def sync_federal_register_agencies() -> dict[str, int]:
    """Fetch Federal Register agencies and upsert them as entities."""
    payload = await federal_register.fetch_agencies()
    async with worker_db_factory() as db:
        parsed = await federal_register.upsert_agencies(db, payload)
    return {"parsed": parsed}


async def sync_wikidata_entities() -> dict[str, int]:
    """Fetch Wikidata entities with official sites and upsert them."""
    payload = await wikidata.fetch_entities()
    async with worker_db_factory() as db:
        parsed = await wikidata.upsert_entities(db, payload)
    return {"parsed": parsed}
