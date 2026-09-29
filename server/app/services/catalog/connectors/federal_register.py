"""Federal Register connector: ingest U.S. federal agencies as primary entities."""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FEDERAL_REGISTER_AGENCIES_URL
from app.crud.catalog import entities as entity_crud
from app.models.enums import EntityType
from app.services.catalog.connectors.base import EntitySeed, fetch_json
from app.services.catalog.gatekeeper import canonical_domain_from_url
from app.typing.catalog import PrimaryEntityCreate

logger = structlog.get_logger(__name__)


def parse_agencies(payload: Any) -> list[EntitySeed]:
    """Parse the Federal Register agencies payload into entity seeds.

    Only agencies exposing a usable website become entities, since ``canonical_domain`` is
    required by the catalog.
    """
    results = payload.get("results", []) if isinstance(payload, dict) else []
    seeds: list[EntitySeed] = []
    seen: set[str] = set()
    for agency in results:
        if not isinstance(agency, dict):
            continue
        name = agency.get("name")
        domain = canonical_domain_from_url(agency.get("url") or agency.get("website") or "")
        if not name or not domain or domain in seen:
            continue
        seen.add(domain)
        seeds.append(
            EntitySeed(
                name=str(name),
                entity_type=EntityType.GOV_FEDERAL,
                canonical_domain=domain,
                jurisdiction="US",
            )
        )
    return seeds


async def fetch_agencies() -> Any:
    """Fetch the Federal Register agencies document."""
    return await fetch_json(FEDERAL_REGISTER_AGENCIES_URL)


async def upsert_agencies(db: AsyncSession, payload: Any) -> int:
    """Upsert parsed agencies as primary entities. Returns the number parsed."""
    seeds = parse_agencies(payload)
    for seed in seeds:
        await entity_crud.create_entity(
            db,
            data=PrimaryEntityCreate(
                name=seed.name,
                entity_type=seed.entity_type,
                canonical_domain=seed.canonical_domain,
                jurisdiction=seed.jurisdiction,
            ),
        )
    return len(seeds)
