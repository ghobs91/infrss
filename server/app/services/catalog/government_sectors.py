"""Subcategory classification for government sources in the catalog.

The catalog browse groups government entities under a single "My Government" section. As that
section grows it is split by ``sector``; curated seeds store a sector explicitly, while older
entities (mostly Federal Register agencies) fall back to this name/domain heuristic at read time.
Slugs here are stable API values; display labels live in the web client.
"""

from __future__ import annotations

import re

from app.models.enums import EntityType

# ``bus`` is matched on a word boundary: a plain substring match would misclassify anything
# containing "business" (e.g. "Farm Production and Conservation Business Center") as transit.
_BUS_RE = re.compile(r"\bbus(es)?\b")

GOVERNMENT_SECTORS = (
    "transit",
    "transportation",
    "health",
    "commerce",
    "finance",
    "science",
    "environment",
    "defense",
    "justice",
    "labor",
    "housing",
    "education",
    "international",
    "local",
    "other",
)


def infer_government_sector(
    *,
    name: str,
    canonical_domain: str,
    entity_type: EntityType,
) -> str:
    """Best-effort subcategory for an unclassified government entity.

    Ordered from most specific to most general. Returns ``"local"`` for state/local government
    bodies that don't match a department keyword, and ``"other"`` for unmatched federal bodies.
    """
    text = f"{name} {canonical_domain}".lower().replace("-", " ").replace("_", " ")

    def has(*needles: str) -> bool:
        return any(needle in text for needle in needles)

    # Transit agencies before general transportation departments.
    if has(
        "transit",
        "transportation authority",
        "rapid transit",
        "metro transit",
        "public transport",
        "rail",
        "metro",
        "ferry",
        "tram",
        "amtrak",
    ) or _BUS_RE.search(text):
        return "transit"
    if has(
        "transportation",
        "transport",
        "highway",
        "aviation",
        "railroad",
        "maritime",
        "motor carrier",
        "traffic safety",
        "pipeline",
        "caltrans",
        "department of motor vehicles",
        "motor vehicle",
    ):
        return "transportation"
    if has(
        "health",
        "nhs",
        "medicare",
        "medicaid",
        "drug administration",
        "disease",
        "institutes of health",
        "human services",
        "substance abuse",
        "health resources",
        "indian health",
        "aging",
        "hhs.gov",
        "nih.gov",
        "child support",
        "disability",
        "food safety",
        "medicine",
    ):
        return "health"
    if has(
        "commerce",
        "economic development",
        "economic",
        "census",
        "patent",
        "trademark",
        "trade",
        "small business",
        "minority business",
        "standards and technology",
        "nist",
        "regional commission",
        "regional authority",
        "textile",
        "consumer product",
        "postal",
        "industry",
        "federal acquisition regulation",
    ):
        return "commerce"
    if has(
        "securities",
        "financial",
        "reserve",
        "monetary",
        "bank",
        "treasury",
        "budget",
        "credit",
        "tax",
        "revenue",
        "insurance",
        "fiscal",
        "currency",
        "commodity futures",
        "accounting",
        "engraving",
        "retirement thrift",
        "accountability",
    ):
        return "finance"
    if has(
        "space",
        "aeronautics",
        "science",
        "geological",
        "oceanic",
        "atmospheric",
        "energy",
        "nuclear",
        "research",
        "communications",
        "noaa",
        "geographic",
        "artificial intelligence",
    ):
        return "science"
    if has(
        "environment",
        "agriculture",
        "forest",
        "fish",
        "wildlife",
        "park",
        "land management",
        "reclamation",
        "climate",
        "conservation",
        "ecosystem",
        "marine mammal",
        "caldera",
        "agricultural marketing",
        "agricultural library",
        "agricultural statistics",
        "advocacy and outreach",
    ):
        return "environment"
    if has(
        "defense",
        "military",
        "army",
        "navy",
        "air force",
        "marine corps",
        "coast guard",
        "veterans",
        "homeland",
        "armed forces",
        "battle monuments",
        "intelligence",
        "national security agency",
    ):
        return "defense"
    if has(
        "justice",
        "court",
        "law",
        "legal",
        "attorney",
        "investigation",
        "prison",
        "corrections",
        "copyright",
        "firearms",
        "civil rights",
        "emergency management",
        "first responder",
        "secret service",
        "special counsel",
        "customs and border",
        "immigration and customs",
        "victims of crime",
        "federal register",
        "records",
        "archives",
        "hearings and appeals",
    ):
        return "justice"
    if has(
        "labor",
        "employment",
        "workforce",
        "occupational",
        "dol.gov",
        "mediation and conciliation",
        "merit systems protection",
        "blind",
    ):
        return "labor"
    if has(
        "housing",
        "urban development",
        "homeless",
        "homeowners",
        "mortgage",
        "hud.gov",
    ):
        return "housing"
    if has(
        "education",
        "student",
        "school",
        "university",
        "college",
        "scholarship",
        "fellowship",
        "library",
        "humanities",
        "assessment governing",
        "udall",
        "institute of american indian",
    ):
        return "education"
    if has(
        "international",
        "foreign",
        "development agency",
        "foreign aid",
        "embassy",
        "broadcasting",
        "inter american",
        "friendship commission",
        "development foundation",
        "millennium challenge",
    ):
        return "international"

    return "local" if entity_type is EntityType.GOV_STATE else "other"
