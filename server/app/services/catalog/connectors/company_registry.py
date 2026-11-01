"""Curated source registry: seed major corporate and institutional primary sources.

The registry connectors (Federal Register, Wikidata) discover agencies and generic
organisations, but the corporate and institutional primary sources users ask for first -
automaker and technology newsrooms, central banks, space and research agencies - are a small,
well-known set that autodiscovery alone surfaces slowly and inconsistently. This connector ships
those as curated entity seeds; the standard discovery + gatekeeper pipeline then locates and
verifies their own newsroom / investor-relations feeds. Assigning a :class:`FeedCategory` is what
lets the catalog browse group sources by industry.

The lists are intentionally hand-maintained: adding an entry here is the supported way to put an
organisation's newsroom in the catalog. Each entry may also carry known-good ``feeds`` URLs; those
are seeded as candidate catalog feeds directly (autodiscovery rarely finds newsroom feeds that
live on a subdomain or bespoke path). When a feed lives on an organisation-owned *alternate*
domain (``github.blog``, ``shopify.engineering``, ``store.steampowered.com``), the host is
recorded as an entity-level ``feed_host`` so the gatekeeper still treats it as first-party.
Domains must be the organisation's own canonical domain (not a social or aggregator host) or the
gatekeeper will (correctly) reject its feeds.
"""

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.catalog import entities as entity_crud
from app.crud.catalog import feeds as feed_crud
from app.models.enums import CatalogFeedType, EntityType, FeedCategory
from app.services.catalog.connectors.base import EntitySeed
from app.services.catalog.gatekeeper import domain_from_url, is_domain_aligned, registrable_domain
from app.typing.catalog import CatalogFeedCreate, PrimaryEntityCreate

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CompanySeed:
    """A curated source (company or institution) before it is expanded into an :class:`EntitySeed`."""

    name: str
    domain: str
    category: FeedCategory | None
    entity_type: EntityType = EntityType.CORP_PUBLIC
    # Known-good feed URLs (RSS/Atom) to seed directly, in addition to autodiscovery.
    feeds: tuple[str, ...] = ()
    # Subcategory within a section (government sources: transit, health, commerce, ...).
    sector: str | None = None


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
        feeds=(
            "https://pressroom.toyota.com/product/feed/atom/",
            "https://newsroom.toyota.eu/feed/",
        ),
    ),
    CompanySeed(
        "Lexus",
        "lexus.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://pressroom.lexus.com/feed/atom/",),
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
    CompanySeed("MINI", "mini.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Rolls-Royce Motor Cars",
        "rolls-roycemotorcars.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://newsroom.rolls-roycemotorcars.com/feed/",),
    ),
    CompanySeed("Mercedes-Benz Group", "mercedes-benz.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Honda Motor Company",
        "honda.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=(
            "https://hondanews.com/en-US/rss",
            "https://hondanews.eu/eu/en/cars/rss/pressreleases/feed.rss",
        ),
    ),
    CompanySeed(
        "Acura",
        "acura.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://acuranews.com/en-US/rss",),
    ),
    CompanySeed(
        "Hyundai Motor Group",
        "hyundai.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.hyundainews.com/rss",),
    ),
    CompanySeed(
        "Genesis",
        "genesis.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://newsroom.genesis.com/feed/",),
    ),
    CompanySeed(
        "Nissan Motor Corporation",
        "nissan-global.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=(
            "https://global.nissannews.com/en/rss",
            "https://europe.nissannews.com/en-GB/rss",
        ),
    ),
    CompanySeed("Infiniti", "infiniti.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Stellantis", "stellantis.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Maserati", "maserati.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Ferrari", "ferrari.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Aston Martin", "astonmartin.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "McLaren",
        "mclaren.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        EntityType.CORP_PRIVATE,
    ),
    CompanySeed("Rivian", "rivian.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Volvo Cars", "volvocars.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Polestar",
        "polestar.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://media.polestar.com/rss",),
    ),
    CompanySeed("Porsche", "porsche.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Audi",
        "audi.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.audi.com/en/feeds/press-releases",),
    ),
    CompanySeed(
        "Skoda",
        "skoda-auto.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.skoda-storyboard.com/en/feed/",),
    ),
    CompanySeed("Bentley", "bentleymotors.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Lamborghini", "lamborghini.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed(
        "Bugatti",
        "bugatti.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        EntityType.CORP_PRIVATE,
    ),
    CompanySeed(
        "Kia",
        "kia.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://www.kiamedia.com/us/maryland/rss/PressKits/feed.rss",),
    ),
    CompanySeed(
        "Mitsubishi Motors",
        "mitsubishi-motors.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://media.mitsubishicars.com/en-US/rss",),
    ),
    CompanySeed(
        "Subaru",
        "subaru.com",
        FeedCategory.AUTOMOTIVE_TRANSPORT,
        feeds=("https://media.subaru.com/rss.do",),
    ),
    CompanySeed("Mazda", "mazda.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Suzuki", "globalsuzuki.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
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
    CompanySeed(
        "OpenAI",
        "openai.com",
        FeedCategory.SOFTWARE_ENGINEERING,
        EntityType.CORP_PRIVATE,
        feeds=("https://openai.com/blog/rss.xml",),
    ),
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
    # ---------------------------------------------------------- More automotive & transport
    CompanySeed("Jaguar Land Rover", "jaguarlandrover.com", FeedCategory.AUTOMOTIVE_TRANSPORT, EntityType.CORP_PRIVATE),
    CompanySeed("PACCAR", "paccar.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Lucid Motors", "lucidmotors.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Renault Group", "renaultgroup.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Tata Motors", "tatamotors.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Mahindra", "mahindra.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("BYD", "bydglobal.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("NIO", "nio.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("XPeng", "xpeng.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Geely", "geely.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Great Wall Motor", "gwm-global.com", FeedCategory.AUTOMOTIVE_TRANSPORT),
    CompanySeed("Isuzu", "isuzu.co.jp", FeedCategory.AUTOMOTIVE_TRANSPORT),
    # --------------------------------------------------------------- Business & finance
    CompanySeed(
        "Nasdaq",
        "nasdaq.com",
        FeedCategory.BUSINESS_FINANCE,
        feeds=("https://www.nasdaq.com/feed/rssoutbound?category=Markets",),
    ),
    # ----------------------------------------------------------------------------- Gaming
    CompanySeed(
        "PlayStation",
        "playstation.com",
        FeedCategory.GAMING,
        feeds=("https://blog.playstation.com/feed/",),
    ),
    CompanySeed(
        "Xbox",
        "xbox.com",
        FeedCategory.GAMING,
        feeds=("https://news.xbox.com/en-us/feed/",),
    ),
    CompanySeed(
        "Valve",
        "valvesoftware.com",
        FeedCategory.GAMING,
        EntityType.CORP_PRIVATE,
        feeds=("https://store.steampowered.com/feeds/news.xml",),
    ),
    CompanySeed(
        "Capcom",
        "capcom.com",
        FeedCategory.GAMING,
        feeds=("https://press.capcom.com/rss",),
    ),
    CompanySeed(
        "CD Projekt",
        "cdprojekt.com",
        FeedCategory.GAMING,
        feeds=("https://www.cdprojekt.com/pl/feed/", "https://cdprojekt.com/en/rss/"),
    ),
    CompanySeed(
        "Krafton",
        "krafton.com",
        FeedCategory.GAMING,
        feeds=("https://www.krafton.com/feed/",),
    ),
    CompanySeed(
        "Unity",
        "unity.com",
        FeedCategory.GAMING,
        feeds=("https://unity.com/blog/feed",),
    ),
    CompanySeed(
        "GOG",
        "gog.com",
        FeedCategory.GAMING,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.gog.com/news/feed",),
    ),
    CompanySeed(
        "Zynga",
        "zynga.com",
        FeedCategory.GAMING,
        feeds=("https://www.zynga.com/feed/",),
    ),
    CompanySeed(
        "505 Games",
        "505games.com",
        FeedCategory.GAMING,
        EntityType.CORP_PRIVATE,
        feeds=("https://505games.com/feed/",),
    ),
    CompanySeed(
        "Rovio",
        "rovio.com",
        FeedCategory.GAMING,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.rovio.com/feed",),
    ),
    CompanySeed(
        "Take-Two Interactive",
        "take2games.com",
        FeedCategory.GAMING,
        feeds=("https://ir.take2games.com/rss/news-releases.xml",),
    ),
    CompanySeed(
        "Raw Fury",
        "rawfury.com",
        FeedCategory.GAMING,
        EntityType.CORP_PRIVATE,
        feeds=("https://rawfury.com/news/feed",),
    ),
    CompanySeed(
        "Team17",
        "team17.com",
        FeedCategory.GAMING,
        feeds=("https://www.team17.com/news/rss.xml",),
    ),
    CompanySeed(
        "Rebellion",
        "rebellion.com",
        FeedCategory.GAMING,
        EntityType.CORP_PRIVATE,
        feeds=("https://rebellion.com/feed/",),
    ),
    CompanySeed(
        "Behaviour Interactive",
        "bhvr.com",
        FeedCategory.GAMING,
        EntityType.CORP_PRIVATE,
        feeds=("https://media.bhvr.com/feed",),
    ),
    CompanySeed(
        "NCSoft",
        "ncsoft.com",
        FeedCategory.GAMING,
        feeds=("https://press.ncsoft.com/rss",),
    ),
    CompanySeed(
        "Sega Sammy Holdings",
        "segasammy.co.jp",
        FeedCategory.GAMING,
        feeds=("https://www.segasammy.co.jp/en/ir/rss/",),
    ),
    CompanySeed(
        "Stillfront Group",
        "stillfront.com",
        FeedCategory.GAMING,
        feeds=("https://stillfront.com/en/ir/rss/",),
    ),
    CompanySeed(
        "Modern Times Group",
        "mtg.com",
        FeedCategory.GAMING,
        feeds=("https://mtg.com/rss",),
    ),
    # ------------------------------------------------------------------ Home & hobbies
    CompanySeed(
        "Husqvarna Group",
        "husqvarnagroup.com",
        FeedCategory.HOME_HOBBIES,
        feeds=("https://husqvarnagroup.com/rss.xml",),
    ),
    CompanySeed(
        "SharkNinja",
        "sharkninja.com",
        FeedCategory.HOME_HOBBIES,
        feeds=("https://newsroom.sharkninja.com/feed/",),
    ),
    # --------------------------------------------------------- Industry & infrastructure
    CompanySeed(
        "Siemens",
        "siemens.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://press.siemens.com/rss.xml",),
    ),
    CompanySeed(
        "GE Vernova",
        "gevernova.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://gevernova.com/rss.xml",),
    ),
    CompanySeed(
        "AECOM",
        "aecom.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://aecom.com/press-releases/feed/",),
    ),
    CompanySeed(
        "Kiewit",
        "kiewit.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.kiewit.com/newsroom/feed/",),
    ),
    CompanySeed(
        "Bechtel",
        "bechtel.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.bechtel.com/media/blog/feed/",),
    ),
    CompanySeed(
        "Vertiv",
        "vertiv.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://vertiv.com/feed",),
    ),
    # ------------------------------------------------------------------- Style & shopping
    CompanySeed(
        "Nike",
        "nike.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://about.nike.com/en/feed",),
    ),
    CompanySeed(
        "H&M Group",
        "hmgroup.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://hmgroup.com/feed/",),
    ),
    CompanySeed(
        "Levi Strauss & Co.",
        "levistrauss.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://levistrauss.com/feed",),
    ),
    CompanySeed(
        "The Estée Lauder Companies",
        "elcompanies.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://elcompanies.com/rss",),
    ),
    # ----------------------------------------------------------- Science & research (corp)
    CompanySeed(
        "Springer Nature",
        "nature.com",
        FeedCategory.SCIENCE_NATURE,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.nature.com/nature.rss",),
    ),
    # ------------------------------------------------------------------- AI & research labs
    CompanySeed(
        "Google DeepMind",
        "deepmind.google",
        FeedCategory.SOFTWARE_ENGINEERING,
        EntityType.CORP_PRIVATE,
        feeds=("https://deepmind.google/blog/rss.xml",),
    ),
    CompanySeed(
        "Google Research",
        "research.google",
        FeedCategory.SOFTWARE_ENGINEERING,
        EntityType.CORP_PRIVATE,
        feeds=("https://research.google/blog/rss/",),
    ),
    # -------------------- Arts & culture
    CompanySeed(
        "Guggenheim",
        "guggenheim.org",
        FeedCategory.ARTS_CULTURE,
        EntityType.CORP_PRIVATE,
        feeds=("https://guggenheim.org/feed",),
    ),
    CompanySeed(
        "Hachette Book Group",
        "hachettebookgroup.com",
        FeedCategory.ARTS_CULTURE,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.hachettebookgroup.com/feed/",),
    ),
    CompanySeed(
        "Museum of Modern Art",
        "moma.org",
        FeedCategory.ARTS_CULTURE,
        EntityType.CORP_PRIVATE,
        feeds=("https://press.moma.org/feed/",),
    ),
    # -------------------- Business & finance
    CompanySeed(
        "PayPal",
        "paypal.com",
        FeedCategory.BUSINESS_FINANCE,
        feeds=("https://newsroom.paypal-corp.com/news?pagetemplate=rss",),
    ),
    # -------------------- Entertainment
    CompanySeed(
        "Live Nation",
        "livenation.com",
        FeedCategory.ENTERTAINMENT,
        feeds=("https://newsroom.livenation.com/feed",),
    ),
    CompanySeed(
        "NBCUniversal",
        "nbcuniversal.com",
        FeedCategory.ENTERTAINMENT,
        feeds=("https://nbcuniversal.com/rss.xml",),
    ),
    CompanySeed(
        "Sony Pictures",
        "sonypictures.com",
        FeedCategory.ENTERTAINMENT,
        feeds=("https://sonypictures.com/rss.xml",),
    ),
    CompanySeed(
        "The Walt Disney Company",
        "thewaltdisneycompany.com",
        FeedCategory.ENTERTAINMENT,
        feeds=("https://thewaltdisneycompany.com/feed/",),
    ),
    CompanySeed(
        "Universal Music Group",
        "universalmusic.com",
        FeedCategory.ENTERTAINMENT,
        feeds=("https://universalmusic.com/feed",),
    ),
    CompanySeed(
        "Warner Music Group",
        "wmg.com",
        FeedCategory.ENTERTAINMENT,
        feeds=("https://www.wmg.com/feed",),
    ),
    # -------------------- Family & relationships
    CompanySeed(
        "Boys & Girls Clubs of America",
        "bgca.org",
        FeedCategory.FAMILY_RELATIONSHIPS,
        EntityType.CORP_PRIVATE,
        feeds=("https://bgca.org/feed",),
    ),
    CompanySeed(
        "Family Equality",
        "familyequality.org",
        FeedCategory.FAMILY_RELATIONSHIPS,
        EntityType.CORP_PRIVATE,
        feeds=("https://familyequality.org/feed/",),
    ),
    # -------------------- Food & drink
    CompanySeed(
        "Diageo",
        "diageo.com",
        FeedCategory.FOOD_DRINK,
        feeds=("https://diageo.com/rss",),
    ),
    CompanySeed(
        "Tyson Foods",
        "tysonfoods.com",
        FeedCategory.FOOD_DRINK,
        feeds=("https://tysonfoods.com/rss.xml",),
    ),
    # -------------------- Health & wellness
    CompanySeed(
        "Medtronic",
        "medtronic.com",
        FeedCategory.HEALTH_WELLNESS,
        feeds=("https://news.medtronic.com/press-releases?pagetemplate=rss",),
    ),
    CompanySeed(
        "Merck",
        "merck.com",
        FeedCategory.HEALTH_WELLNESS,
        feeds=("https://merck.com/feed",),
    ),
    CompanySeed(
        "Moderna",
        "modernatx.com",
        FeedCategory.HEALTH_WELLNESS,
        feeds=("https://news.modernatx.com/feed/rss2",),
    ),
    # -------------------- Home & hobbies
    CompanySeed(
        "Bosch Home",
        "bosch-home.com",
        FeedCategory.HOME_HOBBIES,
        EntityType.CORP_PRIVATE,
        feeds=("https://press.bosch-home.com/rss/current_news/127379",),
    ),
    # -------------------- Civil rights & advocacy
    CompanySeed(
        "GLAAD",
        "glaad.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://glaad.org/feed/",),
    ),
    CompanySeed(
        "Lambda Legal",
        "lambdalegal.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://lambdalegal.org/feed/",),
    ),
    CompanySeed(
        "Native American Rights Fund",
        "narf.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://narf.org/feed",),
    ),
    CompanySeed(
        "UnidosUS",
        "unidosus.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://unidosus.org/feed/",),
    ),
    # -------------------- Industry & infrastructure
    CompanySeed(
        "FedEx",
        "fedex.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://newsroom.fedex.com/index.rss",),
    ),
    CompanySeed(
        "Ferrovial",
        "ferrovial.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://www.ferrovial.com/en/news/feed/",),
    ),
    CompanySeed(
        "GE Aerospace",
        "geaerospace.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://geaerospace.com/rss.xml",),
    ),
    CompanySeed(
        "NextEra Energy",
        "nexteraenergy.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        feeds=("https://newsroom.nexteraenergy.com/news-releases?pagetemplate=rss",),
    ),
    CompanySeed(
        "U.S. Chamber of Commerce",
        "uschamber.com",
        FeedCategory.INDUSTRY_PROFESSIONS,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.uschamber.com/rss/feed.rss",),
    ),
    # -------------------- News & current events
    CompanySeed(
        "ICRC",
        "icrc.org",
        FeedCategory.NEWS_CURRENT_EVENTS,
        EntityType.CORP_PRIVATE,
        feeds=("https://icrc.org/en/rss/general",),
    ),
    # -------------------- Science & nature
    CompanySeed(
        "IUCN",
        "iucn.org",
        FeedCategory.SCIENCE_NATURE,
        EntityType.CORP_PRIVATE,
        feeds=("https://iucn.org/rss.xml",),
    ),
    CompanySeed(
        "PLOS",
        "plos.org",
        FeedCategory.SCIENCE_NATURE,
        EntityType.CORP_PRIVATE,
        feeds=("https://plos.org/feed",),
    ),
    # -------------------- Society, law & history
    CompanySeed(
        "ACLU",
        "aclu.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.aclu.org/press-releases/feed/",),
    ),
    CompanySeed(
        "Amnesty International",
        "amnesty.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.amnesty.org/en/feed/",),
    ),
    CompanySeed(
        "Committee to Protect Journalists",
        "cpj.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://cpj.org/feed/",),
    ),
    CompanySeed(
        "Freedom House",
        "freedomhouse.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://freedomhouse.org/rss.xml",),
    ),
    CompanySeed(
        "Human Rights Watch",
        "hrw.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://hrw.org/rss",),
    ),
    CompanySeed(
        "ICIJ",
        "icij.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.icij.org/category/news/feed/",),
    ),
    CompanySeed(
        "NAACP Legal Defense Fund",
        "naacpldf.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.naacpldf.org/feed/",),
    ),
    CompanySeed(
        "ProPublica",
        "propublica.org",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.propublica.org/feeds/propublica/main",),
    ),
    # -------------------- Sports
    CompanySeed(
        "AEW",
        "allelitewrestling.com",
        FeedCategory.SPORTS,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.allelitewrestling.com/blog-feed.xml",),
    ),
    CompanySeed(
        "Bundesliga",
        "bundesliga.com",
        FeedCategory.SPORTS,
        EntityType.CORP_PRIVATE,
        feeds=("https://bundesliga.com/feed",),
    ),
    CompanySeed(
        "NCAA",
        "ncaa.org",
        FeedCategory.SPORTS,
        EntityType.CORP_PRIVATE,
        feeds=("https://www.ncaa.org/feed/",),
    ),
    CompanySeed(
        "UFC",
        "ufc.com",
        FeedCategory.SPORTS,
        EntityType.CORP_PRIVATE,
        feeds=("https://ufc.com/rss.xml",),
    ),
    CompanySeed(
        "WWE",
        "wwe.com",
        FeedCategory.SPORTS,
        feeds=("https://wwe.com/rss.xml",),
    ),
    # -------------------- Style & shopping
    CompanySeed(
        "Deckers Brands",
        "deckers.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://deckers.com/rss.xml",),
    ),
    CompanySeed(
        "Ralph Lauren",
        "ralphlauren.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://www.ralphlauren.com/rss-feed",),
    ),
    CompanySeed(
        "Skechers",
        "skechers.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://about.skechers.com/feed",),
    ),
    CompanySeed(
        "Tapestry",
        "tapestry.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://www.tapestry.com/feed/",),
    ),
    CompanySeed(
        "VF Corporation",
        "vfc.com",
        FeedCategory.STYLE_SHOPPING,
        feeds=("https://www.vfc.com/investors/news-events-presentations/press-releases/rss",),
    ),
    # -------------------- Travel & geography
    CompanySeed(
        "Booking Holdings",
        "bookingholdings.com",
        FeedCategory.TRAVEL_GEOGRAPHY,
        feeds=("https://www.bookingholdings.com/home/feed/",),
    ),
    CompanySeed(
        "Carnival Corporation",
        "carnivalcorp.com",
        FeedCategory.TRAVEL_GEOGRAPHY,
        feeds=("https://www.carnivalcorp.com/feed/",),
    ),
    CompanySeed(
        "Hyatt",
        "hyatt.com",
        FeedCategory.TRAVEL_GEOGRAPHY,
        feeds=("https://newsroom.hyatt.com/news-releases?pagetemplate=rss",),
    ),
)

# Curated public institutions (agencies, central banks, universities, research bodies). Kept
# separate from the company list because the gatekeeper and category rules are the same but the
# entity type is not corporate; the discovery + verification pipeline treats them identically.
CURATED_INSTITUTIONS: tuple[CompanySeed, ...] = (
    # --------------------------------------------------------- Financial regulators & central banks
    CompanySeed(
        "U.S. Securities and Exchange Commission",
        "sec.gov",
        FeedCategory.BUSINESS_FINANCE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.sec.gov/news/pressreleases.rss",),
    ),
    CompanySeed(
        "Federal Reserve",
        "federalreserve.gov",
        FeedCategory.BUSINESS_FINANCE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.federalreserve.gov/feeds/press_all.xml",),
    ),
    CompanySeed(
        "Bank of England",
        "bankofengland.co.uk",
        FeedCategory.BUSINESS_FINANCE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.bankofengland.co.uk/rss/news",),
    ),
    CompanySeed(
        "European Central Bank",
        "ecb.europa.eu",
        FeedCategory.BUSINESS_FINANCE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.ecb.europa.eu/rss/press.html",),
    ),
    # ------------------------------------------------------------- Space, climate & energy agencies
    CompanySeed(
        "NASA",
        "nasa.gov",
        FeedCategory.SCIENCE_NATURE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.nasa.gov/feed/",),
    ),
    CompanySeed(
        "European Space Agency",
        "esa.int",
        FeedCategory.SCIENCE_NATURE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.esa.int/rssfeed/Our_Activities/Space_News",),
    ),
    CompanySeed(
        "NOAA",
        "noaa.gov",
        FeedCategory.SCIENCE_NATURE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.noaa.gov/rss.xml",),
    ),
    CompanySeed(
        "U.S. Department of Energy",
        "energy.gov",
        FeedCategory.SCIENCE_NATURE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.energy.gov/rss.xml",),
    ),
    # ----------------------------------------------------------------- University & lab research
    CompanySeed(
        "MIT",
        "mit.edu",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://news.mit.edu/rss/feed",),
    ),
    CompanySeed(
        "CERN",
        "home.cern",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://home.cern/news/rss",),
    ),
    CompanySeed(
        "AAAS / Science",
        "science.org",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://www.science.org/rss/news_current.xml",),
    ),
    # -------------------- Business & finance
    CompanySeed(
        "Bank for International Settlements",
        "bis.org",
        FeedCategory.BUSINESS_FINANCE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://bis.org/rss.xml",),
    ),
    CompanySeed(
        "FDIC",
        "fdic.gov",
        FeedCategory.BUSINESS_FINANCE,
        EntityType.GOV_FEDERAL,
        feeds=("https://fdic.gov/rss.xml",),
    ),
    # -------------------- Family & relationships
    CompanySeed(
        "Child Mind Institute",
        "childmind.org",
        FeedCategory.FAMILY_RELATIONSHIPS,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://childmind.org/feed/",),
    ),
    CompanySeed(
        "Zero to Three",
        "zerotothree.org",
        FeedCategory.FAMILY_RELATIONSHIPS,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://zerotothree.org/feed",),
    ),
    # -------------------- Health & wellness
    CompanySeed(
        "NHS England",
        "england.nhs.uk",
        FeedCategory.HEALTH_WELLNESS,
        EntityType.GOV_FEDERAL,
        feeds=("https://england.nhs.uk/feed",),
    ),
    # -------------------- News & current events
    CompanySeed(
        "United Nations",
        "un.org",
        FeedCategory.NEWS_CURRENT_EVENTS,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://news.un.org/feed/subscribe/en/news/all/rss.xml",),
    ),
    # -------------------- Regional & local
    CompanySeed(
        "City of Austin",
        "austintexas.gov",
        FeedCategory.REGIONAL_LOCAL,
        EntityType.GOV_STATE,
        feeds=("https://austintexas.gov/rss.xml",),
    ),
    CompanySeed(
        "City of Boston",
        "boston.gov",
        FeedCategory.REGIONAL_LOCAL,
        EntityType.GOV_STATE,
        feeds=("https://boston.gov/rss.xml",),
    ),
    CompanySeed(
        "City of Portland",
        "portland.gov",
        FeedCategory.REGIONAL_LOCAL,
        EntityType.GOV_STATE,
        feeds=("https://www.portland.gov/news/rss",),
    ),
    CompanySeed(
        "City of Seattle",
        "seattle.gov",
        FeedCategory.REGIONAL_LOCAL,
        EntityType.GOV_STATE,
        feeds=("https://news.seattle.gov/feed/",),
    ),
    # -------------------- Science & nature
    CompanySeed(
        "CNRS",
        "cnrs.fr",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://news.cnrs.fr/rss",),
    ),
    CompanySeed(
        "EPA",
        "epa.gov",
        FeedCategory.SCIENCE_NATURE,
        EntityType.GOV_FEDERAL,
        feeds=("https://epa.gov/rss.xml",),
    ),
    CompanySeed(
        "Fermilab",
        "fnal.gov",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
    ),
    CompanySeed(
        "Harvard University",
        "harvard.edu",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://news.harvard.edu/gazette/feed/",),
    ),
    CompanySeed(
        "NIH",
        "nih.gov",
        FeedCategory.SCIENCE_NATURE,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.nih.gov/rss.xml",),
    ),
    CompanySeed(
        "Stanford University",
        "stanford.edu",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
    ),
    CompanySeed(
        "University of Cambridge",
        "cam.ac.uk",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://cam.ac.uk/feed",),
    ),
    CompanySeed(
        "Woods Hole Oceanographic Institution",
        "whoi.edu",
        FeedCategory.SCIENCE_NATURE,
        EntityType.RESEARCH_ACADEMIC,
        feeds=("https://www.whoi.edu/feed/",),
    ),
    # -------------------- Society, law & history
    CompanySeed(
        "National Archives",
        "archives.gov",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.GOV_FEDERAL,
        feeds=("https://www.archives.gov/rss.xml",),
    ),
    CompanySeed(
        "United States Courts",
        "uscourts.gov",
        FeedCategory.SOCIETY_LAW_HISTORY,
        EntityType.GOV_FEDERAL,
        feeds=("https://uscourts.gov/feed",),
    ),
    # -------------------- Transit agencies
    CompanySeed(
        "AC Transit",
        "actransit.org",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://actransit.org/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "Amtrak",
        "amtrak.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://media.amtrak.com/feed/",),
        sector="transit",
    ),
    CompanySeed(
        "Caltrain",
        "caltrain.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://caltrain.com/news/rss",),
        sector="transit",
    ),
    CompanySeed(
        "Greater Cleveland Regional Transit Authority",
        "riderta.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://riderta.com/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "Massachusetts Bay Transportation Authority",
        "mbta.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://mbta.com/news/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "Metra",
        "metra.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://metra.com/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "Pace",
        "pacebus.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://pacebus.com/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "Renfe",
        "renfe.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://blog.renfe.com/feed/",),
        sector="transit",
    ),
    CompanySeed(
        "San Diego Metropolitan Transit System",
        "sdmts.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://sdmts.com/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "San Francisco Municipal Transportation Agency",
        "sfmta.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://sfmta.com/blog/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "SunRail",
        "sunrail.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://sunrail.com/feed/",),
        sector="transit",
    ),
    CompanySeed(
        "Sydney Metro",
        "sydneymetro.info",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://sydneymetro.info/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "Transport for Ireland",
        "transportforireland.ie",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://transportforireland.ie/feed",),
        sector="transit",
    ),
    CompanySeed(
        "Transport for NSW",
        "transport.nsw.gov.au",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://transport.nsw.gov.au/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "TriMet",
        "trimet.org",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://news.trimet.org/feed/",),
        sector="transit",
    ),
    CompanySeed(
        "Metro Transit (St. Louis)",
        "metrostlouis.org",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.metrostlouis.org/feed/",),
        sector="transit",
    ),
    CompanySeed(
        "VIA Metropolitan Transit",
        "viainfo.net",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.viainfo.net/feed/",),
        sector="transit",
    ),
    CompanySeed(
        "Société de transport de Montréal",
        "stm.info",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.stm.info/en/rss.xml",),
        sector="transit",
    ),
    CompanySeed(
        "Sacramento Regional Transit",
        "sacrt.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.sacrt.com/feed/",),
        sector="transit",
    ),
    # -------------------- Commerce & economic development departments (Federal)
    CompanySeed(
        "Bureau of Economic Analysis",
        "bea.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://bea.gov/rss",),
        sector="commerce",
    ),
    CompanySeed(
        "International Trade Administration",
        "trade.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://trade.gov/rss.xml",),
        sector="commerce",
    ),
    CompanySeed(
        "National Telecommunications and Information Administration",
        "ntia.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://ntia.gov/rss.xml",),
        sector="commerce",
    ),
    CompanySeed(
        "U.S. Patent and Trademark Office",
        "uspto.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://uspto.gov/rss.xml",),
        sector="commerce",
    ),
    # -------------------- Commerce & economic development departments (State)
    CompanySeed(
        "California Governor's Office of Business and Economic Development",
        "business.ca.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://business.ca.gov/feed/",),
        sector="commerce",
    ),
    CompanySeed(
        "Colorado Office of Economic Development and International Trade",
        "oedit.colorado.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://oedit.colorado.gov/rss.xml",),
        sector="commerce",
    ),
    CompanySeed(
        "Kansas Department of Commerce",
        "kansascommerce.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://kansascommerce.gov/feed",),
        sector="commerce",
    ),
    CompanySeed(
        "Montana Department of Commerce",
        "commerce.mt.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        sector="commerce",
    ),
    CompanySeed(
        "North Dakota Department of Commerce",
        "commerce.nd.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.commerce.nd.gov/rss/news",),
        sector="commerce",
    ),
    CompanySeed(
        "Utah Governor's Office of Economic Opportunity",
        "business.utah.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://business.utah.gov/feed/",),
        sector="commerce",
    ),
    CompanySeed(
        "Vermont Agency of Commerce and Community Development",
        "accd.vermont.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://accd.vermont.gov/rss.xml",),
        sector="commerce",
    ),
    CompanySeed(
        "Washington State Department of Commerce",
        "commerce.wa.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.commerce.wa.gov/feed/",),
        sector="commerce",
    ),
    # -------------------- Health departments (Federal)
    CompanySeed(
        "Food and Drug Administration",
        "fda.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Office of the National Coordinator for Health IT",
        "healthit.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://healthit.gov/feed/",),
        sector="health",
    ),
    # -------------------- Health departments (Local)
    CompanySeed(
        "DC Health",
        "dchealth.dc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dchealth.dc.gov/node/%2A/newsroom",),
        sector="health",
    ),
    # -------------------- Health departments (State)
    CompanySeed(
        "Delaware Health and Social Services",
        "dhss.delaware.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dhss.delaware.gov/feed/",),
        sector="health",
    ),
    CompanySeed(
        "Florida Department of Health",
        "floridahealth.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://floridahealth.gov/feed",),
        sector="health",
    ),
    CompanySeed(
        "Georgia Department of Public Health",
        "dph.georgia.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dph.georgia.gov/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Hawaii Department of Health",
        "health.hawaii.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://health.hawaii.gov/feed",),
        sector="health",
    ),
    CompanySeed(
        "Idaho Department of Health and Welfare",
        "healthandwelfare.idaho.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://healthandwelfare.idaho.gov/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Iowa Department of Health and Human Services",
        "hhs.iowa.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://hhs.iowa.gov/news/50/all/all/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Minnesota Department of Health",
        "health.state.mn.us",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://health.state.mn.us/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Mississippi State Department of Health",
        "msdh.ms.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://msdh.ms.gov/msdhsite/rssFeed.xml",),
        sector="health",
    ),
    CompanySeed(
        "Montana Department of Public Health and Human Services",
        "dphhs.mt.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        sector="health",
    ),
    CompanySeed(
        "North Carolina Department of Health and Human Services",
        "ncdhhs.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ncdhhs.gov/news/feed",),
        sector="health",
    ),
    CompanySeed(
        "North Dakota Health and Human Services",
        "hhs.nd.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.hhs.nd.gov/rss/news",),
        sector="health",
    ),
    CompanySeed(
        "Rhode Island Department of Health",
        "health.ri.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://health.ri.gov/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "South Carolina Department of Public Health",
        "dph.sc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dph.sc.gov/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Texas Department of State Health Services",
        "dshs.texas.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dshs.texas.gov/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Vermont Department of Health",
        "healthvermont.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.healthvermont.gov/taxonomy/term/126/feed",),
        sector="health",
    ),
    CompanySeed(
        "Virginia Department of Health",
        "vdh.virginia.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.vdh.virginia.gov/feed/",),
        sector="health",
    ),
    CompanySeed(
        "Wisconsin Department of Health Services",
        "dhs.wisconsin.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dhs.wisconsin.gov/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "Wyoming Department of Health",
        "health.wyo.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://health.wyo.gov/feed/",),
        sector="health",
    ),
    # -------------------- Cities & local government (Local)
    CompanySeed(
        "City of San Diego",
        "sandiego.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://sandiego.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "San Diego County",
        "sandiegocounty.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.sandiegocounty.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Washington, D.C.",
        "dc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dc.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "City of Cleveland",
        "clevelandohio.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.clevelandohio.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Governor of California",
        "gov.ca.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.gov.ca.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Governor of Washington",
        "governor.wa.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.governor.wa.gov/rss.xml",),
        sector="local",
    ),
    # -------------------- Transportation departments (Federal)
    CompanySeed(
        "Federal Aviation Administration",
        "faa.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://www.faa.gov/blog/cleared_for_takeoff/rss.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "National Transportation Safety Board",
        "ntsb.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://www.ntsb.gov/rss.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "Surface Transportation Board",
        "stb.gov",
        category=None,
        entity_type=EntityType.GOV_FEDERAL,
        feeds=("https://stb.gov/feed",),
        sector="transportation",
    ),
    # -------------------- Transportation departments (Local)
    CompanySeed(
        "DC Department of Transportation",
        "ddot.dc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ddot.dc.gov/node/%2A/newsroom",),
        sector="transportation",
    ),
    # -------------------- Transportation departments (State)
    CompanySeed(
        "Colorado Department of Transportation",
        "codot.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.codot.gov/RSS",),
        sector="transportation",
    ),
    CompanySeed(
        "Idaho Transportation Department",
        "itd.idaho.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://itd.idaho.gov/feed",),
        sector="transportation",
    ),
    CompanySeed(
        "Iowa Department of Transportation",
        "iowadot.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://iowadot.gov/news/5/all/all/rss.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "Missouri Department of Transportation",
        "modot.org",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://modot.org/rss.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "New Mexico Department of Transportation",
        "dot.nm.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.dot.nm.gov/feed/",),
        sector="transportation",
    ),
    CompanySeed(
        "North Dakota Department of Transportation",
        "dot.nd.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.dot.nd.gov/rss/news/All/All",),
        sector="transportation",
    ),
    CompanySeed(
        "Utah Department of Transportation",
        "udot.utah.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://connect.udot.utah.gov/feed/",),
        sector="transportation",
    ),
    CompanySeed(
        "Vermont Agency of Transportation",
        "vtrans.vermont.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://vtrans.vermont.gov/taxonomy/term/1/feed",),
        sector="transportation",
    ),
    CompanySeed(
        "Washington State Department of Transportation",
        "wsdot.wa.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://wsdot.wa.gov/rss.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "West Virginia Department of Transportation",
        "transportation.wv.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://transportation.wv.gov/rss.xml",),
        sector="transportation",
    ),
    # -------------------- State governors / state portals
    CompanySeed(
        "Office of the Governor of Alabama",
        "governor.alabama.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.alabama.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Alaska",
        "gov.alaska.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://gov.alaska.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Arizona",
        "azgovernor.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://azgovernor.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Arkansas",
        "governor.arkansas.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.arkansas.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "State of Colorado",
        "colorado.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.colorado.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Delaware",
        "governor.delaware.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.delaware.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Georgia",
        "gov.georgia.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://gov.georgia.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Hawaii",
        "governor.hawaii.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.hawaii.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Idaho",
        "gov.idaho.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://gov.idaho.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Mississippi",
        "governorreeves.ms.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governorreeves.ms.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Missouri",
        "governor.mo.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.mo.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Nebraska",
        "governor.nebraska.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.nebraska.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of North Carolina",
        "governor.nc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.nc.gov/news/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of North Dakota",
        "governor.nd.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.governor.nd.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Utah",
        "governor.utah.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.utah.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of Vermont",
        "governor.vermont.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.vermont.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "Office of the Governor of West Virginia",
        "governor.wv.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://governor.wv.gov/rss.xml",),
        sector="local",
    ),
    # -------------------- State attorneys general / justice departments
    CompanySeed(
        "Alabama Attorney General",
        "alabamaag.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.alabamaag.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Arizona Attorney General",
        "azag.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.azag.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Arkansas Attorney General",
        "arkansasag.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://arkansasag.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "California Attorney General",
        "oag.ca.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.oag.ca.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Colorado Attorney General",
        "coag.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://coag.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Delaware Attorney General",
        "attorneygeneral.delaware.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://attorneygeneral.delaware.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "District of Columbia Attorney General",
        "oag.dc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://oag.dc.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Florida Attorney General",
        "myfloridalegal.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.myfloridalegal.com/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Georgia Attorney General",
        "law.georgia.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://law.georgia.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Hawaii Attorney General",
        "ag.hawaii.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ag.hawaii.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Idaho Attorney General",
        "ag.idaho.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.ag.idaho.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Mississippi Attorney General",
        "attorneygenerallynnfitch.com",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://attorneygenerallynnfitch.com/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Missouri Attorney General",
        "ago.mo.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ago.mo.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Montana Department of Justice",
        "dojmt.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dojmt.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Nebraska Attorney General",
        "ago.nebraska.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ago.nebraska.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "New Jersey Attorney General",
        "njoag.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.njoag.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "New Mexico Department of Justice",
        "nmdoj.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://nmdoj.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "North Carolina Department of Justice",
        "ncdoj.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ncdoj.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "North Dakota Attorney General",
        "attorneygeneral.nd.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://attorneygeneral.nd.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Oregon Department of Justice",
        "doj.state.or.us",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.doj.state.or.us/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Pennsylvania Attorney General",
        "attorneygeneral.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.attorneygeneral.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Rhode Island Attorney General",
        "riag.ri.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://riag.ri.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Utah Attorney General",
        "attorneygeneral.utah.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://attorneygeneral.utah.gov/feed/",),
        sector="justice",
    ),
    CompanySeed(
        "Vermont Attorney General",
        "ago.vermont.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ago.vermont.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Washington Attorney General",
        "atg.wa.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.atg.wa.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "West Virginia Attorney General",
        "ago.wv.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ago.wv.gov/rss.xml",),
        sector="justice",
    ),
    # -------------------- Additional state health & transportation sources
    CompanySeed(
        "Arkansas Department of Health",
        "healthy.arkansas.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://healthy.arkansas.gov/feed/",),
        sector="health",
    ),
    CompanySeed(
        "Maine Department of Health and Human Services",
        "maine.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.maine.gov/tools/feeds/DHS+Press+Releases.rss",),
        sector="health",
    ),
    CompanySeed(
        "Arkansas Department of Transportation",
        "ardot.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ardot.gov/feed/",),
        sector="transportation",
    ),
    # -------------------- New York State agencies
    CompanySeed(
        "New York State Department of Transportation",
        "dot.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.dot.ny.gov/rss/press-releases.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "New York State Department of Motor Vehicles",
        "dmv.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dmv.ny.gov/rss.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "New York State Thruway Authority",
        "thruway.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://thruway.ny.gov/rss.xml",),
        sector="transportation",
    ),
    CompanySeed(
        "New York State Education Department",
        "nysed.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://www.nysed.gov/rss.xml",),
        sector="education",
    ),
    CompanySeed(
        "New York State Department of Environmental Conservation",
        "dec.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dec.ny.gov/rss.xml",),
        sector="environment",
    ),
    CompanySeed(
        "New York State Department of Agriculture and Markets",
        "agriculture.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://agriculture.ny.gov/rss.xml",),
        sector="environment",
    ),
    CompanySeed(
        "New York State Office of Parks, Recreation and Historic Preservation",
        "parks.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://parks.ny.gov/rss.xml",),
        sector="environment",
    ),
    CompanySeed(
        "New York State Department of Labor",
        "dol.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dol.ny.gov/rss.xml",),
        sector="labor",
    ),
    CompanySeed(
        "New York State Office for People With Developmental Disabilities",
        "opwdd.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://opwdd.ny.gov/rss.xml",),
        sector="health",
    ),
    CompanySeed(
        "New York State Division of Homeland Security and Emergency Services",
        "dps.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dps.ny.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "New York State Division of Criminal Justice Services",
        "criminaljustice.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://criminaljustice.ny.gov/rss.xml",),
        sector="justice",
    ),
    CompanySeed(
        "Empire State Development",
        "esd.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://esd.ny.gov/rss.xml",),
        sector="commerce",
    ),
    CompanySeed(
        "New York State Homes and Community Renewal",
        "hcr.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://hcr.ny.gov/rss.xml",),
        sector="housing",
    ),
    CompanySeed(
        "New York State Office of Information Technology Services",
        "its.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://its.ny.gov/rss.xml",),
        sector="science",
    ),
    CompanySeed(
        "New York State Department of State",
        "dos.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://dos.ny.gov/rss.xml",),
        sector="local",
    ),
    CompanySeed(
        "New York State Office of General Services",
        "ogs.ny.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://ogs.ny.gov/rss.xml",),
        sector="other",
    ),
    # -------------------- New York City government
    CompanySeed(
        "New York City Council",
        "council.nyc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://council.nyc.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "New York City Comptroller",
        "comptroller.nyc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://comptroller.nyc.gov/feed/",),
        sector="finance",
    ),
    CompanySeed(
        "Manhattan Borough President",
        "manhattanbp.nyc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://manhattanbp.nyc.gov/feed/",),
        sector="local",
    ),
    CompanySeed(
        "Queens Borough President",
        "queensbp.nyc.gov",
        category=None,
        entity_type=EntityType.GOV_STATE,
        feeds=("https://queensbp.nyc.gov/feed/",),
        sector="local",
    ),
)


def infer_feed_type(url: str) -> CatalogFeedType:
    """Best-effort feed type from a known URL (verification re-checks the real document)."""
    lowered = (url or "").lower().rstrip("/")
    if lowered.endswith("atom") or ".atom" in lowered or "/atom" in lowered:
        return CatalogFeedType.NATIVE_ATOM
    return CatalogFeedType.NATIVE_RSS


def _entity_feed_hosts(domain: str, feeds: tuple[str, ...]) -> tuple[str, ...]:
    """First-party alternate domains among ``feeds`` - company-owned, outside ``domain``.

    Recording the registrable domain (``fb.com`` for ``engineering.fb.com``) keeps the
    registry declarative and consistent: every feed on that owned domain aligns, so a
    second newsroom feed cannot be rejected while the first one passes.
    """
    hosts: list[str] = []
    for url in feeds:
        host = domain_from_url(url)
        if not host or is_domain_aligned(host, domain):
            continue
        alternate = registrable_domain(host)
        if alternate and alternate not in hosts:
            hosts.append(alternate)
    return tuple(hosts)


def build_entity_seeds() -> list[EntitySeed]:
    """Expand the curated lists into deduplicated entity seeds.

    Domains are normalized to their canonical form (lower-cased, trailing dot and leading
    ``www.`` stripped) so a company is catalogued once even if the list is edited carelessly.
    """
    seeds: list[EntitySeed] = []
    seen: set[str] = set()
    for company in (*CURATED_COMPANIES, *CURATED_INSTITUTIONS):
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
                sector=company.sector,
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
                sector=seed.sector,
                feed_hosts=list(seed.feed_hosts),
            ),
        )
        if entity is None:
            # Blocked by the editorial source policy (app.utils.source_policy).
            continue
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
