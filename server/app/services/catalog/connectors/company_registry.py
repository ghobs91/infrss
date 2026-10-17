"""Curated company registry: seed major corporate primary sources.

The registry connectors (Federal Register, Wikidata) discover agencies and generic
organisations, but the corporate primary sources users ask for first - automaker and
technology newsrooms - are a small, well-known set that autodiscovery alone surfaces
slowly and inconsistently. This connector ships those companies as curated entity
seeds; the standard discovery + gatekeeper pipeline then locates and verifies their own
newsroom / investor-relations feeds. Assigning a :class:`FeedCategory` is what lets the
catalog browse group sources by industry.

The list is intentionally hand-maintained: adding a company here is the supported way to
put its newsroom in the catalog. Each entry may also carry known-good ``feeds`` URLs; those
are seeded as candidate catalog feeds directly (autodiscovery rarely finds newsroom feeds
that live on a subdomain or bespoke path). When a feed lives on a company-owned *alternate*
domain (``github.blog``, ``shopify.engineering``, ``engineering.fb.com``), the host is
recorded as an entity-level ``feed_host`` so the gatekeeper still treats it as first-party.
Domains must be the organisation's own canonical domain (not a social or aggregator host) or
the gatekeeper will (correctly) reject its feeds.
"""

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.catalog import entities as entity_crud
from app.crud.catalog import feeds as feed_crud
from app.models.enums import CatalogFeedType, EntityType, FeedCategory
from app.services.catalog.connectors.base import EntitySeed
from app.services.catalog.gatekeeper import domain_from_url, is_domain_aligned
from app.typing.catalog import CatalogFeedCreate, PrimaryEntityCreate

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CompanySeed:
    """A curated company before it is expanded into an :class:`EntitySeed`."""

    name: str
    domain: str
    category: FeedCategory
    entity_type: EntityType = EntityType.CORP_PUBLIC
    # Known-good feed URLs (RSS/Atom) to seed directly, in addition to autodiscovery.
    feeds: tuple[str, ...] = ()


CURATED_COMPANIES: tuple[CompanySeed, ...] = (
    # ------------------------------------------------------------------ Automotive & transport
    CompanySeed("Tesla", "tesla.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Ford Motor Company",
        "ford.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
    ),
    CompanySeed("General Motors", "gm.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Toyota Motor Corporation",
        "toyota.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://pressroom.toyota.com/product/feed/atom/",),
    ),
    CompanySeed(
        "Volkswagen Group",
        "volkswagen-group.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.volkswagen-newsroom.com/en/feeds/press-releases",),
    ),
    CompanySeed(
        "BMW Group",
        "bmwgroup.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=(
            "https://www.press.bmwgroup.com/global/rss/topic/803",
            "https://www.press.bmwgroup.com/global/rss/topic/5236",
            "https://www.press.bmwgroup.com/global/rss/topic/4100",
        ),
    ),
    CompanySeed("Mercedes-Benz Group", "mercedes-benz.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Honda Motor Company", "honda.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Hyundai Motor Group", "hyundai.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Nissan Motor Corporation",
        "nissan-global.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://global.nissannews.com/en/rss",),
    ),
    CompanySeed("Stellantis", "stellantis.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Rivian", "rivian.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Volvo Cars", "volvocars.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Porsche", "porsche.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Audi",
        "audi.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.audi.com/en/feeds/press-releases",),
    ),
    CompanySeed(
        "Kia",
        "kia.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.kiamedia.com/us/maryland/rss/PressKits/feed.rss",),
    ),
    CompanySeed(
        "Cummins",
        "cummins.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.cummins.com/rss.xml",),
    ),
    # ------------------------------------------------------------------ Consumer technology
    CompanySeed(
        "Apple",
        "apple.com",
        FeedCategory.CONSUMER_TECH_DIGITAL,
        feeds=("https://machinelearning.apple.com/rss.xml",),
    ),
    CompanySeed("Google", "google.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    CompanySeed(
        "Microsoft",
        "microsoft.com",
        FeedCategory.CONSUMER_TECH_DIGITAL,
    ),
    CompanySeed(
        "Amazon",
        "amazon.com",
        FeedCategory.CONSUMER_TECH_DIGITAL,
        feeds=("https://aws.amazon.com/blogs/aws/feed/",),
    ),
    CompanySeed(
        "Meta",
        "meta.com",
        FeedCategory.CONSUMER_TECH_DIGITAL,
        feeds=("https://engineering.fb.com/feed/",),
    ),
    CompanySeed(
        "NVIDIA",
        "nvidia.com",
        FeedCategory.CONSUMER_TECH_DIGITAL,
        feeds=("https://blogs.nvidia.com/feed/",),
    ),
    CompanySeed("Samsung Electronics", "samsung.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    CompanySeed("Sony", "sony.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    CompanySeed("Intel", "intel.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    CompanySeed("AMD", "amd.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    CompanySeed(
        "Netflix",
        "netflix.com",
        FeedCategory.CONSUMER_TECH_DIGITAL,
        feeds=("https://netflixtechblog.com/feed",),
    ),
    CompanySeed("Adobe", "adobe.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    CompanySeed("IBM", "ibm.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    CompanySeed("Qualcomm", "qualcomm.com", FeedCategory.CONSUMER_TECH_DIGITAL),
    # ------------------------------------------------- Software, AI & enterprise technology
    CompanySeed("OpenAI", "openai.com", FeedCategory.SOFTWARE_ENGINEERING, EntityType.CORP_PRIVATE),
    CompanySeed("Anthropic", "anthropic.com", FeedCategory.SOFTWARE_ENGINEERING, EntityType.CORP_PRIVATE),
    CompanySeed(
        "Salesforce",
        "salesforce.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://engineering.salesforce.com/feed",),
    ),
    CompanySeed("Oracle", "oracle.com", FeedCategory.SOFTWARE_ENGINEERING),
    CompanySeed(
        "Cisco",
        "cisco.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://blogs.cisco.com/feed",),
    ),
    CompanySeed("Arm", "arm.com", FeedCategory.SOFTWARE_ENGINEERING),
    CompanySeed(
        "Cloudflare",
        "cloudflare.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://blog.cloudflare.com/rss",),
    ),
    CompanySeed(
        "Stripe",
        "stripe.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        EntityType.CORP_PRIVATE,
        feeds=("https://stripe.com/blog/feed.rss",),
    ),
    CompanySeed(
        "Lyft",
        "lyft.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://eng.lyft.com/feed",),
    ),
    CompanySeed(
        "MongoDB",
        "mongodb.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://www.mongodb.com/blog/rss",),
    ),
    CompanySeed(
        "DigitalOcean",
        "digitalocean.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://www.digitalocean.com/community/tutorials/feed",),
    ),
    CompanySeed(
        "Confluent",
        "confluent.io",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://www.confluent.io/feed/",),
    ),
    CompanySeed(
        "Twilio",
        "twilio.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://www.twilio.com/blog/feed",),
    ),
    CompanySeed(
        "Yelp",
        "yelp.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://engineeringblog.yelp.com/feed.xml",),
    ),
    CompanySeed(
        "Zalando",
        "zalando.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://engineering.zalando.com/atom.xml",),
    ),
    CompanySeed(
        "Instacart",
        "instacart.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://tech.instacart.com/feed",),
    ),
    CompanySeed(
        "Grab",
        "grab.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://engineering.grab.com/feed.xml",),
    ),
    CompanySeed(
        "Auth0",
        "auth0.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://auth0.com/blog/rss.xml",),
    ),
    CompanySeed(
        "Hugging Face",
        "huggingface.co",
        FeedCategory.SOFTWARE_ENGINEERING,
        EntityType.CORP_PRIVATE,
        feeds=("https://huggingface.co/blog/feed.xml",),
    ),
    CompanySeed(
        "Shopify",
        "shopify.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://shopify.engineering/blog.atom",),
    ),
    CompanySeed(
        "Slack",
        "slack.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://slack.engineering/feed",),
    ),
    CompanySeed(
        "Spotify",
        "spotify.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://engineering.atspotify.com/feed",),
    ),
    CompanySeed(
        "GitHub",
        "github.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://github.blog/feed/",),
    ),
    CompanySeed(
        "Dropbox",
        "dropbox.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        feeds=("https://dropbox.tech/feed",),
    ),
)


def infer_feed_type(url: str) -> CatalogFeedType:
    """Best-effort feed type from a known URL (verification re-checks the real document)."""
    lowered = (url or "").lower().rstrip("/")
    if lowered.endswith("atom") or ".atom" in lowered or "/atom" in lowered:
        return CatalogFeedType.NATIVE_ATOM
    return CatalogFeedType.NATIVE_RSS


def _entity_feed_hosts(domain: str, feeds: tuple[str, ...]) -> tuple[str, ...]:
    """Hosts of ``feeds`` that are not aligned with ``domain`` - company-owned alternate domains.

    Deriving these from the feed URLs keeps the registry declarative: adding a feed on
    ``github.blog`` automatically records that host for the entity.
    """
    hosts: list[str] = []
    for url in feeds:
        host = domain_from_url(url)
        if host and not is_domain_aligned(host, domain) and host not in hosts:
            hosts.append(host)
    return tuple(hosts)


def build_entity_seeds() -> list[EntitySeed]:
    """Expand the curated list into deduplicated entity seeds.

    Domains are normalized to their canonical form (lower-cased, trailing dot and leading
    ``www.`` stripped) so a company is catalogued once even if the list is edited carelessly.
    """
    seeds: list[EntitySeed] = []
    seen: set[str] = set()
    for company in CURATED_COMPANIES:
        domain = (company.domain or "").strip().lower().rstrip(".")
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain or domain in seen:
            continue
        seen.add(domain)
        seeds.append(
            EntitySeed(
                name=company.name,
                entity_type=company.entity_type,
                canonical_domain=domain,
                category=company.category,
                feeds=company.feeds,
                feed_hosts=_entity_feed_hosts(domain, company.feeds),
            )
        )
    return seeds


async def upsert_companies(db: AsyncSession, seeds: list[EntitySeed] | None = None) -> dict[str, int]:
    """Persist curated company entities and their known feeds.

    Returns counts of entities processed and candidate feeds created (or already present).
    """
    resolved = build_entity_seeds() if seeds is None else seeds
    feeds_created = 0
    for seed in resolved:
        entity = await entity_crud.create_entity(
            db,
            data=PrimaryEntityCreate(
                name=seed.name,
                entity_type=seed.entity_type,
                canonical_domain=seed.canonical_domain,
                category=seed.category,
                feed_hosts=list(seed.feed_hosts),
            ),
        )
        for feed_url in seed.feeds:
            await feed_crud.create_catalog_feed(
                db,
                data=CatalogFeedCreate(
                    entity_id=entity.id,
                    feed_url=feed_url,
                    feed_type=infer_feed_type(feed_url),
                ),
            )
            feeds_created += 1
    logger.info("Upserted curated companies", entities=len(resolved), feeds=feeds_created)
    return {"entities": len(resolved), "feeds": feeds_created}
