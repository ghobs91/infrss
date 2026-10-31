"""Integrity checks for the primary-source catalog seed snapshot.

The snapshot in ``scripts/data/catalog_seed.json`` is applied to every deployment at boot, so a
malformed one ships a broken Discover page to everyone. These tests need no database: they verify
the file parses, its references resolve, and its enum values still exist.
"""

import json
from pathlib import Path

import pytest

from app.models.enums import CatalogFeedType, EntityType, FeedCategory, VerificationStatus

SEED_PATH = Path(__file__).parent.parent.parent / "scripts" / "data" / "catalog_seed.json"


@pytest.fixture(scope="module")
def seed() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def test_snapshot_is_not_empty(seed: dict) -> None:
    """An empty snapshot would silently produce an empty catalog on every fresh install."""
    assert len(seed["entities"]) > 0
    assert len(seed["feeds"]) > 0


def test_entity_keys_are_unique(seed: dict) -> None:
    """Both are ON CONFLICT targets, so duplicates would be dropped silently instead of erroring."""
    entities = seed["entities"]
    assert len({e["canonical_domain"] for e in entities}) == len(entities)
    assert len({e["id"] for e in entities}) == len(entities)


def test_feed_keys_are_unique(seed: dict) -> None:
    feeds = seed["feeds"]
    assert len({f["feed_url"] for f in feeds}) == len(feeds)
    assert len({f["id"] for f in feeds}) == len(feeds)


def test_every_feed_resolves_to_a_seeded_entity(seed: dict) -> None:
    """entity_id is resolved by domain, so an unknown domain means the feed is never inserted."""
    domains = {e["canonical_domain"] for e in seed["entities"]}
    orphaned = sorted({f["entity_domain"] for f in seed["feeds"]} - domains)
    assert not orphaned, f"feeds reference unseeded entities: {orphaned[:5]}"


def test_entity_enums_are_valid(seed: dict) -> None:
    allowed_types = {e.value for e in EntityType}
    allowed_categories = {c.value for c in FeedCategory}
    for entity in seed["entities"]:
        assert entity["entity_type"] in allowed_types, entity["canonical_domain"]
        category = entity["category"]
        assert category is None or category in allowed_categories, entity["canonical_domain"]


def test_feed_enums_are_valid(seed: dict) -> None:
    allowed_types = {t.value for t in CatalogFeedType}
    allowed_statuses = {s.value for s in VerificationStatus}
    for feed in seed["feeds"]:
        assert feed["feed_type"] in allowed_types, feed["feed_url"]
        assert feed["verification_status"] in allowed_statuses, feed["feed_url"]
