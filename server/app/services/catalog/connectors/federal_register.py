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


def _agency_rows(payload: Any) -> list[dict[str, Any]]:
    """Return the agency objects from either a bare list or a ``{"results": [...]}`` envelope."""
    if isinstance(payload, dict):
        rows = payload.get("results", [])
    elif isinstance(payload, list):
        rows = payload
    else:
        return []
    return [row for row in rows if isinstance(row, dict)]


def parse_agencies(payload: Any) -> list[EntitySeed]:
    """Parse the Federal Register agencies payload into entity seeds.

    Only agencies exposing a usable website become entities, since ``canonical_domain`` is
    required by the catalog. The agency's own site is ``agency_url``; the ``url`` field points
    at the agency's page on federalregister.gov and must not be treated as the canonical domain.
    """
    seeds: list[EntitySeed] = []
    seen: set[str] = set()
    for agency in _agency_rows(payload):
        name = agency.get("name")
        domain = canonical_domain_from_url(agency.get("agency_url") or "")
        if not name or not domain or domain == "federalregister.gov" or domain in seen:
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
