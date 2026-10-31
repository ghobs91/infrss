#!/usr/bin/env python3
"""Seed the curated primary-source catalog.

`GET /catalog/sources` is normally populated at runtime: the connector sync tasks import
authoritative organisations, `discover_catalog_feeds` finds their feeds, and the verification
scheduler promotes them to VERIFIED_PRIMARY in batches. That takes days — the weekly connectors
only run on Mondays, and verification re-checks 100 feeds every two hours — so a fresh install
shows an empty Discover page and a new deployment looks broken next to an existing one.

`data/catalog_seed.json` is a snapshot of that catalog taken from a converged instance, applied
here so every deployment starts with the same sources.

Idempotent by design: entities are matched on their unique `canonical_domain` and feeds on their
unique `feed_url`, and conflicting rows are left untouched. The api container runs this on every
start, so connector-discovered rows are never duplicated, and a row the pipeline has since
re-classified (e.g. QUARANTINED) is never overwritten by the snapshot.

Volatile columns are deliberately not seeded: etag/last_modified caching headers, poll timestamps
and failure counts all start empty, so the verification pipeline treats the feeds as new work.

Usage:
    python scripts/seed_catalog.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import Text, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY

from app.db.session import get_db_factory

logger = structlog.get_logger(__name__)

SEED_PATH = Path(__file__).parent / "data" / "catalog_seed.json"

# ON CONFLICT DO NOTHING (with no conflict target) covers both the primary key and the natural
# unique key, so a pre-existing row wins regardless of which one collides.
INSERT_ENTITY = text(
    """
    INSERT INTO primary_entities (
        id, name, entity_type, canonical_domain, cik, jurisdiction, sector, category, feed_hosts
    ) VALUES (
        CAST(:id AS uuid),
        :name,
        CAST(:entity_type AS entitytype),
        :canonical_domain,
        :cik,
        :jurisdiction,
        :sector,
        CAST(:category AS feedcategory),
        :feed_hosts
    )
    ON CONFLICT DO NOTHING
    """
).bindparams(bindparam("feed_hosts", type_=ARRAY(Text)))

# entity_id is resolved from the domain rather than trusting the snapshot's UUID: if the entity
# already exists under a different id, the feed still attaches to the row that is actually there.
INSERT_FEED = text(
    """
    INSERT INTO catalog_feeds (
        id, entity_id, feed_url, feed_type, verification_status, rejection_reason,
        outbound_third_party_ratio
    )
    SELECT
        CAST(:id AS uuid),
        e.id,
        :feed_url,
        CAST(:feed_type AS catalogfeedtype),
        CAST(:verification_status AS verificationstatus),
        :rejection_reason,
        :outbound_third_party_ratio
    FROM primary_entities e
    WHERE e.canonical_domain = :entity_domain
    ON CONFLICT DO NOTHING
    """
)


async def seed_catalog() -> tuple[int, int, int, int]:
    """Apply the seed file. Returns (entities added, feeds added, entities in seed, feeds in seed)."""
    payload = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    entities = payload["entities"]
    feeds = payload["feeds"]

    session_factory = await get_db_factory()
    entities_added = 0
    feeds_added = 0

    async with session_factory() as session:
        for entity in entities:
            result = await session.execute(INSERT_ENTITY, entity)
            entities_added += result.rowcount or 0

        for feed in feeds:
            result = await session.execute(INSERT_FEED, feed)
            feeds_added += result.rowcount or 0

        await session.commit()

    return entities_added, feeds_added, len(entities), len(feeds)


async def main() -> None:
    try:
        added_entities, added_feeds, total_entities, total_feeds = await seed_catalog()
    except Exception:
        logger.exception("Failed to seed primary-source catalog")
        sys.exit(1)

    logger.info(
        "Primary-source catalog seeded",
        entities_added=added_entities,
        entities_already_present=total_entities - added_entities,
        feeds_added=added_feeds,
        feeds_already_present=total_feeds - added_feeds,
    )


if __name__ == "__main__":
    asyncio.run(main())
