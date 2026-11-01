"""Unit tests for government sector classification (pure, no network or database)."""

import pytest

from app.models.enums import EntityType
from app.services.catalog.government_sectors import (
    GOVERNMENT_SECTORS,
    infer_government_sector,
)


def _sector(name: str, domain: str = "agency.gov", entity_type: EntityType = EntityType.GOV_FEDERAL) -> str:
    return infer_government_sector(name=name, canonical_domain=domain, entity_type=entity_type)


@pytest.mark.unit
def test_federal_departments_classify_into_their_sectors():
    assert _sector("U.S. Department of Commerce") == "commerce"
    assert _sector("U.S. Department of Health and Human Services") == "health"
    assert _sector("U.S. Department of Transportation") == "transportation"
    assert _sector("Federal Transit Administration") == "transit"
    assert _sector("Metropolitan Transportation Authority") == "transit"


@pytest.mark.unit
def test_state_and_local_departments_use_the_same_sectors():
    assert _sector("California Department of Public Health", "cdph.ca.gov", EntityType.GOV_STATE) == "health"
    assert _sector("Texas Department of Transportation", "txdot.gov", EntityType.GOV_STATE) == "transportation"
    assert _sector("Kansas Department of Commerce", "kansascommerce.gov", EntityType.GOV_STATE) == "commerce"
    # Unmatched state/local bodies default to the local bucket.
    assert _sector("City of Boston", "boston.gov", EntityType.GOV_STATE) == "local"


@pytest.mark.unit
def test_sector_slugs_are_stable():
    assert {"transit", "transportation", "health", "commerce", "local"} <= set(GOVERNMENT_SECTORS)


@pytest.mark.unit
def test_bus_matches_on_word_boundary_not_substring():
    # "Business" must not be read as a bus agency.
    assert _sector("Farm Production and Conservation Business Center") != "transit"
    assert _sector("Metro Bus Company", "metrobus.gov") == "transit"


@pytest.mark.unit
def test_agencies_without_department_keywords_use_mission_keywords():
    assert _sector("Central Intelligence Agency", "cia.gov") == "defense"
    assert _sector("National Security Agency/Central Security Service", "nsa.gov") == "defense"
    assert _sector("Commodity Futures Trading Commission", "cftc.gov") == "finance"
    assert _sector("Comptroller of the Currency", "occ.gov") == "finance"
    assert _sector("Federal Communications Commission", "fcc.gov") == "science"
    assert _sector("National Agricultural Statistics Service", "nass.usda.gov") == "environment"
    assert _sector("Marine Mammal Commission", "mmc.gov") == "environment"
    assert _sector("Library of Congress", "loc.gov") == "education"
    assert _sector("Inter-American Foundation", "iaf.gov") == "international"
    assert _sector("Japan-United States Friendship Commission", "jusfc.gov") == "international"


@pytest.mark.unit
def test_regulatory_and_program_agencies_classify_by_function():
    assert _sector("Federal Emergency Management Agency", "fema.gov") == "justice"
    assert _sector("Federal Register Office", "archives.gov") == "justice"
    assert _sector("Merit Systems Protection Board", "mspb.gov") == "labor"
    assert _sector("Child Support Enforcement Office", "acf.hhs.gov") == "health"
    assert _sector("Government National Mortgage Association", "ginniemae.gov") == "housing"
    assert _sector("Amtrak Reform Council", "govinfo.library.unt.edu") == "transit"


@pytest.mark.unit
def test_truly_unclassified_agencies_stay_in_other():
    # Cultural, legislative-support and government-operations bodies have no topical sector.
    assert _sector("Architect of the Capitol", "aoc.gov") == "other"
    assert _sector("National Endowment for the Arts", "arts.gov") == "other"
