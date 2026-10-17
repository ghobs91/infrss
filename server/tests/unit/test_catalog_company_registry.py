"""Unit tests for the curated company registry connector (pure, no network or database)."""

import pytest

from app.models.enums import CatalogFeedType, EntityType, FeedCategory, VerificationStatus
from app.services.catalog.connectors import company_registry
from app.services.catalog.gatekeeper import evaluate_feed


@pytest.mark.unit
def test_build_entity_seeds_dedupes_and_normalizes_domains():
    seeds = company_registry.build_entity_seeds()
    domains = [seed.canonical_domain for seed in seeds]
    assert domains
    assert len(domains) == len(set(domains))
    assert all(domain == domain.lower() and not domain.startswith("www.") for domain in domains)


@pytest.mark.unit
def test_curated_companies_cover_automotive_and_tech():
    by_domain = {seed.canonical_domain: seed for seed in company_registry.build_entity_seeds()}
    assert by_domain["tesla.com"].category is FeedCategory.AUTOMOTIVE_TRANSPORT
    assert by_domain["kia.com"].category is FeedCategory.AUTOMOTIVE_TRANSPORT
    assert by_domain["apple.com"].category is FeedCategory.CONSUMER_TECH_DIGITAL
    assert by_domain["cloudflare.com"].category is FeedCategory.SOFTWARE_ENGINEERING


@pytest.mark.unit
def test_every_seed_is_named_and_categorized():
    for seed in company_registry.build_entity_seeds():
        assert seed.name
        assert seed.category is not None
        assert seed.entity_type in {EntityType.CORP_PUBLIC, EntityType.CORP_PRIVATE}


@pytest.mark.unit
def test_private_companies_are_marked_private():
    by_domain = {seed.canonical_domain: seed for seed in company_registry.build_entity_seeds()}
    assert by_domain["openai.com"].entity_type is EntityType.CORP_PRIVATE
    assert by_domain["anthropic.com"].entity_type is EntityType.CORP_PRIVATE
    assert by_domain["tesla.com"].entity_type is EntityType.CORP_PUBLIC


@pytest.mark.unit
def test_domain_normalization_drops_www_and_duplicates(monkeypatch):
    monkeypatch.setattr(
        company_registry,
        "CURATED_COMPANIES",
        (
            company_registry.CompanySeed("Example", "www.Example.com", FeedCategory.MISCELLANEOUS),
            company_registry.CompanySeed("Example Dupe", "example.com", FeedCategory.MISCELLANEOUS),
        ),
    )
    seeds = company_registry.build_entity_seeds()
    assert [seed.canonical_domain for seed in seeds] == ["example.com"]
    assert seeds[0].name == "Example"


@pytest.mark.unit
def test_infer_feed_type():
    assert (
        company_registry.infer_feed_type("https://pressroom.toyota.com/product/feed/atom/")
        is CatalogFeedType.NATIVE_ATOM
    )
    assert (
        company_registry.infer_feed_type("https://www.press.bmwgroup.com/global/rss/topic/803")
        is CatalogFeedType.NATIVE_RSS
    )


@pytest.mark.unit
def test_every_seeded_feed_passes_the_gatekeeper():
    """Each seeded feed must verify for its entity, including entity-level alternate hosts."""
    for seed in company_registry.build_entity_seeds():
        for url in seed.feeds:
            verdict = evaluate_feed(
                canonical_domain=seed.canonical_domain,
                feed_url=url,
                item_links=[url],
                extra_allowed_hosts=seed.feed_hosts,
            )
            assert verdict.status is VerificationStatus.VERIFIED_PRIMARY, (
                f"{url} rejected for {seed.canonical_domain}: {verdict.reason}"
            )


@pytest.mark.unit
def test_alternate_domain_feeds_record_entity_feed_hosts():
    by_domain = {seed.canonical_domain: seed for seed in company_registry.build_entity_seeds()}
    assert "github.blog" in by_domain["github.com"].feed_hosts
    assert "shopify.engineering" in by_domain["shopify.com"].feed_hosts
    assert "engineering.fb.com" in by_domain["meta.com"].feed_hosts
    assert "www.kiamedia.com" in by_domain["kia.com"].feed_hosts
    assert "global.nissannews.com" in by_domain["nissan-global.com"].feed_hosts
    # Feeds on the entity's own domain (or a subdomain) must not pollute feed_hosts.
    assert by_domain["cloudflare.com"].feed_hosts == ()
    assert by_domain["bmwgroup.com"].feed_hosts == ()
