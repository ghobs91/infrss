"""Unit tests for catalog connectors' pure parsers (no network, no database)."""

import pytest

from app.models.enums import EntityType
from app.services.catalog.connectors import federal_register, sec, wikidata


@pytest.mark.unit
def test_zero_pad_cik():
    assert sec.zero_pad_cik(320193) == "0000320193"
    assert sec.zero_pad_cik("320193") == "0000320193"
    assert sec.zero_pad_cik("0000320193") == "0000320193"


@pytest.mark.unit
def test_normalize_company_name_strips_legal_suffixes():
    assert sec.normalize_company_name("Apple Inc.") == "apple"
    assert sec.normalize_company_name("Exxon Mobil Corporation") == "exxon mobil"
    assert sec.normalize_company_name("Berkshire Hathaway Inc. Holdings") == "berkshire hathaway"


@pytest.mark.unit
def test_parse_company_tickers():
    payload = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    }
    companies = sec.parse_company_tickers(payload)
    assert [c.cik for c in companies] == ["0000320193", "0000789019"]
    assert companies[0].ticker == "AAPL"


@pytest.mark.unit
def test_parse_company_tickers_tolerates_garbage():
    assert sec.parse_company_tickers(None) == []
    assert sec.parse_company_tickers({"0": "nope", "1": {"title": "No CIK"}}) == []


@pytest.mark.unit
def test_build_sec_atom_url():
    url = sec.build_sec_atom_url(320193)
    assert "CIK=0000320193" in url
    assert "output=atom" in url


@pytest.mark.unit
def test_parse_agencies_skips_agencies_without_site():
    payload = {
        "results": [
            {"name": "Food and Drug Administration", "url": "https://www.fda.gov"},
            {"name": "No Site Agency"},
            {"name": "Also No Site", "url": ""},
        ]
    }
    seeds = federal_register.parse_agencies(payload)
    assert len(seeds) == 1
    assert seeds[0].canonical_domain == "fda.gov"
    assert seeds[0].entity_type is EntityType.GOV_FEDERAL


@pytest.mark.unit
def test_infer_entity_type():
    assert wikidata.infer_entity_type("nasa.gov") is EntityType.GOV_FEDERAL
    assert wikidata.infer_entity_type("mit.edu") is EntityType.RESEARCH_ACADEMIC
    assert wikidata.infer_entity_type("apple.com") is EntityType.CORP_PRIVATE


@pytest.mark.unit
def test_build_sparql_query_has_limit():
    query = wikidata.build_sparql_query(limit=25)
    assert "P856" in query
    assert "LIMIT 25" in query


@pytest.mark.unit
def test_parse_wikidata_entities_dedupes_and_normalizes():
    payload = {
        "results": {
            "bindings": [
                {
                    "entityLabel": {"value": "Apple Inc."},
                    "website": {"value": "https://www.apple.com"},
                    "newsroom": {"value": "https://www.apple.com/newsroom/"},
                },
                {"entityLabel": {"value": "Apple duplicate"}, "website": {"value": "https://apple.com"}},
                {"entityLabel": {"value": "No Website"}},
            ]
        }
    }
    seeds = wikidata.parse_entities(payload)
    assert len(seeds) == 1
    assert seeds[0].canonical_domain == "apple.com"
    assert seeds[0].newsroom_url == "https://www.apple.com/newsroom/"
