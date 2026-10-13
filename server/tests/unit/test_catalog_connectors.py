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
            {
                "name": "Food and Drug Administration",
                "agency_url": "https://www.fda.gov",
                "url": "https://www.federalregister.gov/agencies/food-and-drug-administration",
            },
            {"name": "No Site Agency"},
            {"name": "Also No Site", "agency_url": ""},
        ]
    }
    seeds = federal_register.parse_agencies(payload)
    assert len(seeds) == 1
    assert seeds[0].canonical_domain == "fda.gov"
    assert seeds[0].entity_type is EntityType.GOV_FEDERAL


@pytest.mark.unit
def test_parse_agencies_accepts_bare_list_response():
    """The live /agencies.json endpoint returns a top-level JSON array, not a results envelope."""
    payload = [
        {"name": "Securities and Exchange Commission", "agency_url": "https://www.sec.gov/"},
        {"name": "Duplicate", "agency_url": "https://sec.gov"},
        {"name": "No Site"},
    ]
    seeds = federal_register.parse_agencies(payload)
    assert len(seeds) == 1
    assert seeds[0].canonical_domain == "sec.gov"


@pytest.mark.unit
def test_parse_agencies_ignores_federalregister_self_links():
    """``url`` is the agency's federalregister.gov page, never its own domain."""
    payload = [
        {
            "name": "No Own Site",
            "url": "https://www.federalregister.gov/agencies/no-own-site",
        }
    ]
    assert federal_register.parse_agencies(payload) == []


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


@pytest.mark.asyncio
@pytest.mark.unit
async def test_fetch_entities_sends_sparql_query_and_user_agent(monkeypatch):
    """Without the query param the endpoint 403s; the descriptive UA is also required."""
    captured: dict = {}

    async def fake_fetch_json(url, *, headers=None, params=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        return {"results": {"bindings": []}}

    monkeypatch.setattr(wikidata, "fetch_json", fake_fetch_json)

    await wikidata.fetch_entities(limit=7)

    assert captured["url"] == wikidata.WIKIDATA_SPARQL_ENDPOINT
    assert "P856" in captured["params"]["query"]
    assert "LIMIT 7" in captured["params"]["query"]
    assert captured["headers"]["User-Agent"]
