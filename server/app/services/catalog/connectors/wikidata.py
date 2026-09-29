"""Wikidata connector: discover official sites and newsrooms for primary entities.

Uses SPARQL over the Wikidata Query Service: ``P856`` (official website) supplies the canonical
domain; ``P1018`` supplies an official newsroom URL where present.
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import WIKIDATA_SPARQL_ENDPOINT
from app.crud.catalog import entities as entity_crud
from app.models.enums import EntityType
from app.services.catalog.connectors.base import EntitySeed, fetch_json
from app.services.catalog.gatekeeper import canonical_domain_from_url
from app.typing.catalog import PrimaryEntityCreate

logger = structlog.get_logger(__name__)

DEFAULT_SPARQL_LIMIT = 500

# Official-site statements, with an optional newsroom property.
SPARQL_QUERY_TEMPLATE = """SELECT ?entity ?entityLabel ?website ?newsroom WHERE {{
  ?entity wdt:P856 ?website .
  OPTIONAL {{ ?entity wdt:P1018 ?newsroom . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT {limit}"""


def build_sparql_query(limit: int = DEFAULT_SPARQL_LIMIT) -> str:
    """Build the SPARQL query used to discover entities with an official website."""
    return SPARQL_QUERY_TEMPLATE.format(limit=int(limit))


def infer_entity_type(domain: str) -> EntityType:
    """Heuristically classify an entity from its domain suffix."""
    domain = (domain or "").lower()
    if domain.endswith(".gov") or ".gov." in domain:
        return EntityType.GOV_FEDERAL
    if domain.endswith(".edu") or ".ac." in domain:
        return EntityType.RESEARCH_ACADEMIC
    return EntityType.CORP_PRIVATE


def parse_entities(payload: Any) -> list[EntitySeed]:
    """Parse a Wikidata SPARQL response into entity seeds, one per unique domain."""
    bindings = payload.get("results", {}).get("bindings", []) if isinstance(payload, dict) else []
    seeds: list[EntitySeed] = []
    seen: set[str] = set()
    for row in bindings:
        if not isinstance(row, dict):
            continue
        label = (row.get("entityLabel") or {}).get("value")
        website = (row.get("website") or {}).get("value")
        newsroom = (row.get("newsroom") or {}).get("value")
        domain = canonical_domain_from_url(website or "")
        if not label or not domain or domain in seen:
            continue
        seen.add(domain)
        seeds.append(
            EntitySeed(
                name=str(label),
                entity_type=infer_entity_type(domain),
                canonical_domain=domain,
                newsroom_url=newsroom,
            )
        )
    return seeds


async def fetch_entities(limit: int = DEFAULT_SPARQL_LIMIT) -> Any:
    """Run the SPARQL query against Wikidata and return the raw results document."""
    return await fetch_json(
        WIKIDATA_SPARQL_ENDPOINT,
        headers={"Accept": "application/sparql-results+json"},
    )


async def upsert_entities(db: AsyncSession, payload: Any) -> int:
    """Upsert parsed Wikidata entities. Returns the number parsed."""
    seeds = parse_entities(payload)
    for seed in seeds:
        await entity_crud.create_entity(
            db,
            data=PrimaryEntityCreate(
                name=seed.name,
                entity_type=seed.entity_type,
                canonical_domain=seed.canonical_domain,
            ),
        )
    return len(seeds)
