"""SEC EDGAR connector: CIK mapping and filing Atom endpoints.

SEC's ``company_tickers.json`` carries no website, so this connector cannot invent a
``canonical_domain``. It parses ``(cik, ticker, name)`` records and attaches a CIK to an entity
whose domain was learned elsewhere (Wikidata, Federal Register), plus builds the per-filer Atom
endpoint used as a native feed candidate.
"""

import re
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SEC_ATOM_URL_TEMPLATE, SEC_COMPANY_TICKERS_URL
from app.crud.catalog import entities as entity_crud
from app.services.catalog.connectors.base import RateLimiter, fetch_json

logger = structlog.get_logger(__name__)

# Trailing legal-form tokens stripped when matching SEC filer titles to entity names.
_LEGAL_SUFFIXES = frozenset(
    {
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "llc",
        "lp",
        "ltd",
        "limited",
        "plc",
        "sa",
        "nv",
        "ag",
        "se",
        "holdings",
        "group",
    }
)


@dataclass(frozen=True)
class SecCompany:
    """A filer row from the SEC ticker map."""

    cik: str
    ticker: str | None
    name: str


def zero_pad_cik(cik: str | int) -> str:
    """Zero-pad a CIK to the canonical 10-digit form."""
    return str(int(cik)).zfill(10)


def normalize_company_name(name: str) -> str:
    """Normalize a company name for matching, dropping legal-form suffixes."""
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", name.lower())
    tokens = cleaned.split()
    while tokens and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def parse_company_tickers(payload: Any) -> list[SecCompany]:
    """Parse SEC ``company_tickers.json`` into filer records."""
    if not isinstance(payload, dict):
        return []
    companies: list[SecCompany] = []
    for entry in payload.values():
        if not isinstance(entry, dict):
            continue
        cik = entry.get("cik_str")
        title = entry.get("title")
        if cik is None or not title:
            continue
        ticker = entry.get("ticker")
        companies.append(
            SecCompany(
                cik=zero_pad_cik(cik),
                ticker=str(ticker) if ticker is not None else None,
                name=str(title),
            )
        )
    return companies


def build_sec_atom_url(cik: str | int, filing_type: str = "8-K") -> str:
    """Build the SEC EDGAR Atom feed URL for a filer's filings of one type."""
    return SEC_ATOM_URL_TEMPLATE.format(cik=zero_pad_cik(cik), filing_type=filing_type)


async def fetch_company_tickers(user_agent: str, limiter: RateLimiter) -> Any:
    """Fetch the SEC company tickers map, respecting the SEC fair-access rate limit."""
    await limiter.acquire()
    return await fetch_json(SEC_COMPANY_TICKERS_URL, headers={"User-Agent": user_agent})


async def apply_ciks_to_entities(db: AsyncSession, companies: list[SecCompany]) -> int:
    """Attach CIKs to entities missing one, matching by normalized company name."""
    by_name = {normalize_company_name(company.name): company.cik for company in companies}
    entities = await entity_crud.get_entities_missing_cik(db)
    updated = 0
    for entity in entities:
        cik = by_name.get(normalize_company_name(entity.name))
        if cik:
            entity.cik = cik
            updated += 1
    if updated:
        await db.flush()
    logger.info("Applied SEC CIKs", entities=len(entities), updated=updated)
    return updated
