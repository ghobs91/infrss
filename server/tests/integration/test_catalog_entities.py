"""Integration tests for primary-source entity persistence."""

import pytest

from app.crud.catalog import entities
from app.models.enums import EntityType
from app.typing.catalog import PrimaryEntityCreate


@pytest.mark.asyncio
async def test_create_entity_normalizes_domain(db_session):
    entity = await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(
            name="U.S. Food and Drug Administration",
            entity_type=EntityType.GOV_FEDERAL,
            canonical_domain="FDA.gov",
            jurisdiction="US",
        ),
    )

    assert entity.id is not None
    assert entity.canonical_domain == "fda.gov"

    fetched = await entities.get_entity_by_domain(db_session, canonical_domain="fda.gov")
    assert fetched is not None
    assert fetched.id == entity.id


@pytest.mark.asyncio
async def test_create_entity_is_idempotent_by_domain(db_session):
    data = PrimaryEntityCreate(
        name="Apple Inc.",
        entity_type=EntityType.CORP_PUBLIC,
        canonical_domain="apple.com",
        cik="0000320193",
    )

    first = await entities.create_entity(db_session, data=data)
    second = await entities.create_entity(db_session, data=data)

    assert first.id == second.id
    assert first.cik == "0000320193"
