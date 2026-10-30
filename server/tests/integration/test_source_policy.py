"""Integration test: blocked sources are never ingested into the catalog."""

import pytest

from app.crud.catalog import entities
from app.models.enums import EntityType
from app.typing.catalog import PrimaryEntityCreate


@pytest.mark.asyncio
async def test_create_entity_skips_blocked_domain(db_session):
    entity = await entities.create_entity(
        db_session,
        data=PrimaryEntityCreate(
            name="Blocked Source",
            entity_type=EntityType.CORP_PRIVATE,
            canonical_domain="adl.org",
        ),
    )

    assert entity is None
    assert await entities.get_entity_by_domain(db_session, canonical_domain="adl.org") is None
