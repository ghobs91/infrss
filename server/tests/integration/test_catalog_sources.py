"""Integration tests for the catalog source browse query and entity categories."""

import pytest

from app.crud.catalog import entities, feeds
from app.models.enums import CatalogFeedType, EntityType, FeedCategory, VerificationStatus
from app.typing.catalog import CatalogFeedCreate, GatekeeperResult, PrimaryEntityCreate


async def _entity(
    db_session,
    *,
    name: str,
    domain: str,
    category: FeedCategory | None = None,
    entity_type: EntityType = EntityType.CORP_PUBLIC,
):
    return await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(
            name=name,
            entity_type=entity_type,
            canonical_domain=domain,
            category=category,
        ),
    )


async def _feed_with_status(db_session, entity, *, url: str, status: VerificationStatus):
    feed = await feeds.create_catalog_feed(
        db_session,
        data=CatalogFeedCreate(entity_id=entity.id, feed_url=url, feed_type=CatalogFeedType.NATIVE_RSS),
    )
    await feeds.apply_verification(db_session, feed=feed, result=GatekeeperResult(status=status))
    return feed


@pytest.mark.asyncio
async def test_list_sources_only_returns_entities_with_verified_feeds(db_session):
    verified = await _entity(db_session, name="Ford", domain="ford.com", category=FeedCategory.AUTOMOTIVE_TRANSPORT)
    await _feed_with_status(
        db_session, verified, url="https://ford.com/rss.xml", status=VerificationStatus.VERIFIED_PRIMARY
    )

    pending_only = await _entity(db_session, name="Pending Co", domain="pending.example")
    await _feed_with_status(
        db_session, pending_only, url="https://pending.example/rss.xml", status=VerificationStatus.PENDING
    )

    rows = await entities.list_sources_with_verified_feeds(db_session)

    assert [entity.name for entity, _ in rows] == ["Ford"]
    assert len(rows[0][1]) == 1


@pytest.mark.asyncio
async def test_list_sources_filters_by_category(db_session):
    apple = await _entity(db_session, name="Apple", domain="apple.com", category=FeedCategory.CONSUMER_TECH_DIGITAL)
    await _feed_with_status(
        db_session, apple, url="https://apple.com/rss.xml", status=VerificationStatus.VERIFIED_PRIMARY
    )
    ford = await _entity(db_session, name="Ford", domain="ford.com", category=FeedCategory.AUTOMOTIVE_TRANSPORT)
    await _feed_with_status(
        db_session, ford, url="https://ford.com/rss.xml", status=VerificationStatus.VERIFIED_PRIMARY
    )

    rows = await entities.list_sources_with_verified_feeds(db_session, category=FeedCategory.CONSUMER_TECH_DIGITAL)

    assert [entity.name for entity, _ in rows] == ["Apple"]


@pytest.mark.asyncio
async def test_create_entity_persists_category_and_backfills(db_session):
    first = await _entity(db_session, name="Tesla", domain="tesla.com")
    assert first.category is None

    again = await _entity(db_session, name="Tesla", domain="tesla.com", category=FeedCategory.AUTOMOTIVE_TRANSPORT)

    assert again.id == first.id
    assert again.category is FeedCategory.AUTOMOTIVE_TRANSPORT
