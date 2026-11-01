"""Integrity checks for the primary-source catalog seed snapshot.

The snapshot in ``scripts/data/catalog_seed.json`` is applied to every deployment at boot, so a
malformed one ships a broken Discover page to everyone. These tests need no database: they verify
the file parses, its references resolve, and its enum values still exist.
"""

import json
from pathlib import Path

import pytest

from app.models.enums import CatalogFeedType, EntityType, FeedCategory, VerificationStatus
from app.services.catalog.gatekeeper import domain_from_url, is_domain_aligned, registrable_domain

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


def test_verified_feeds_pass_the_gatekeeper(seed: dict) -> None:
    """Replay the gatekeeper over the snapshot.

    The snapshot was taken from a converged instance, which hid a drift: one feed on an
    entity-owned alternate domain was verified while another on the same owned domain was
    rejected. Re-deriving every verdict here keeps the data and the rules in step.
    """
    entities = {e["canonical_domain"]: e for e in seed["entities"]}
    unexplained = []
    for feed in seed["feeds"]:
        if feed["verification_status"] != "VERIFIED_PRIMARY":
            continue
        entity = entities[feed["entity_domain"]]
        hosts = tuple(entity["feed_hosts"] or ())
        host = domain_from_url(feed["feed_url"])
        if not is_domain_aligned(host, entity["canonical_domain"], hosts):
            unexplained.append((entity["canonical_domain"], host, feed["feed_url"]))
    assert not unexplained, f"verified feeds on unexplained hosts: {unexplained[:5]}"


def test_feed_hosts_are_reviewed_registrable_domains(seed: dict) -> None:
    """Alternate hosts are owned domains, not the one subdomain discovery happened to find."""
    for entity in seed["entities"]:
        hosts = entity["feed_hosts"] or []
        assert len(hosts) == len(set(hosts)), entity["canonical_domain"]
        for host in hosts:
            assert host == registrable_domain(host), (entity["canonical_domain"], host)
            assert not host.startswith("www."), (entity["canonical_domain"], host)
            # A redundant entry would hide a misalignment instead of documenting one.
            assert not is_domain_aligned(host, entity["canonical_domain"]), (
                entity["canonical_domain"],
                host,
            )
