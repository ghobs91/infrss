"""Integration tests for gatekeeper verdict persistence on catalog feeds."""

import pytest

from app.crud.catalog import entities, feeds
from app.models.enums import CatalogFeedType, EntityType, VerificationStatus
from app.services.catalog.gatekeeper import evaluate_feed
from app.typing.catalog import CatalogFeedCreate, PrimaryEntityCreate


async def _make_entity(db_session, domain: str = "fda.gov"):
    return await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(
            name="U.S. Food and Drug Administration",
            entity_type=EntityType.GOV_FEDERAL,
            canonical_domain=domain,
        ),
    )


@pytest.mark.asyncio
async def test_verified_feed_is_persisted(db_session):
    entity = await _make_entity(db_session)
    feed = await feeds.create_catalog_feed(
        db_session,
        data=CatalogFeedCreate(
            entity_id=entity.id,
            feed_url="https://www.fda.gov/about-fda/contact-fda/rss-feeds",
            feed_type=CatalogFeedType.NATIVE_RSS,
        ),
    )

    result = evaluate_feed(
        canonical_domain=entity.canonical_domain,
        feed_url=feed.feed_url,
        item_links=["https://www.fda.gov/news-events/press-announcements/example"],
    )
    verified = await feeds.apply_verification(db_session, feed=feed, result=result)

    assert verified.verification_status is VerificationStatus.VERIFIED_PRIMARY
    assert verified.rejection_reason is None
    assert verified.outbound_third_party_ratio == 0.0
    assert verified.last_polled_at is not None


@pytest.mark.asyncio
async def test_aggregator_feed_is_rejected_and_recorded(db_session):
    entity = await _make_entity(db_session)
    feed = await feeds.create_catalog_feed(
        db_session,
        data=CatalogFeedCreate(
            entity_id=entity.id,
            feed_url="https://feeds.example.com/fda",
            feed_type=CatalogFeedType.NATIVE_RSS,
        ),
    )

    result = evaluate_feed(
        canonical_domain=entity.canonical_domain,
        feed_url=feed.feed_url,
        item_links=[],
    )
    rejected = await feeds.apply_verification(db_session, feed=feed, result=result)

    assert rejected.verification_status is VerificationStatus.REJECTED_AGGREGATOR
    assert rejected.rejection_reason is not None


@pytest.mark.asyncio
async def test_create_catalog_feed_is_idempotent_by_url(db_session):
    entity = await _make_entity(db_session)
    data = CatalogFeedCreate(
        entity_id=entity.id,
        feed_url="https://www.fda.gov/rss.xml",
        feed_type=CatalogFeedType.NATIVE_RSS,
    )

    first = await feeds.create_catalog_feed(db_session, data=data)
    second = await feeds.create_catalog_feed(db_session, data=data)

    assert first.id == second.id
    assert first.verification_status is VerificationStatus.PENDING
