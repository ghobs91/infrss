"""Unit tests for the primary-source gatekeeper (pure logic, no database)."""

import pytest

from app.models.enums import VerificationStatus
from app.services.catalog.gatekeeper import (
    canonical_domain_from_url,
    domain_from_url,
    evaluate_feed,
    is_domain_aligned,
    outbound_third_party_ratio,
    redirect_chain_is_authorized,
)


@pytest.mark.unit
def test_domain_from_url_normalizes_host():
    assert domain_from_url("https://News.Microsoft.com/feed.xml") == "news.microsoft.com"
    assert domain_from_url("HTTPS://FDA.GOV.") == "fda.gov"
    assert domain_from_url("") == ""
    assert domain_from_url("not a url") == ""


@pytest.mark.unit
def test_canonical_domain_from_url_strips_www_and_port():
    assert canonical_domain_from_url("https://www.fda.gov/foo") == "fda.gov"
    assert canonical_domain_from_url("http://FDA.GOV:80/x") == "fda.gov"
    assert canonical_domain_from_url("") == ""


@pytest.mark.unit
def test_is_domain_aligned_accepts_canonical_and_subdomains():
    assert is_domain_aligned("fda.gov", "fda.gov")
    assert is_domain_aligned("www.fda.gov", "fda.gov")
    assert is_domain_aligned("news.microsoft.com", "microsoft.com")


@pytest.mark.unit
def test_is_domain_aligned_rejects_unrelated_and_reverse():
    # Subdomain direction matters: the feed may be a subdomain, never the parent.
    assert not is_domain_aligned("microsoft.com", "news.microsoft.com")
    assert not is_domain_aligned("fake-fda.gov", "fda.gov")
    assert not is_domain_aligned("reuters.com", "fda.gov")
    assert not is_domain_aligned("", "fda.gov")


@pytest.mark.unit
def test_is_domain_aligned_allows_configured_feed_cdns():
    assert is_domain_aligned("feeds.feedburner.com", "example.com")


@pytest.mark.unit
def test_outbound_third_party_ratio():
    assert outbound_third_party_ratio([], "fda.gov") == 0.0
    assert outbound_third_party_ratio(["https://fda.gov/a", "https://www.fda.gov/b"], "fda.gov") == 0.0
    assert outbound_third_party_ratio(["https://reuters.com/a"], "fda.gov") == 1.0
    assert outbound_third_party_ratio(["https://fda.gov/a", "https://reuters.com/b"], "fda.gov") == 0.5


@pytest.mark.unit
def test_redirect_chain_is_authorized():
    assert redirect_chain_is_authorized(["https://fda.gov/feed", "https://www.fda.gov/final"], "fda.gov")
    assert not redirect_chain_is_authorized(["https://aggregator.example/x"], "fda.gov")


@pytest.mark.unit
def test_evaluate_feed_verifies_aligned_low_outbound_feed():
    result = evaluate_feed(
        canonical_domain="fda.gov",
        feed_url="https://www.fda.gov/rss.xml",
        item_links=["https://www.fda.gov/news/1", "https://www.fda.gov/news/2"],
    )
    assert result.status is VerificationStatus.VERIFIED_PRIMARY
    assert result.is_primary
    assert result.outbound_third_party_ratio == 0.0


@pytest.mark.unit
def test_evaluate_feed_rejects_misaligned_host():
    result = evaluate_feed(
        canonical_domain="fda.gov",
        feed_url="https://feeds.example.com/fda",
        item_links=[],
    )
    assert result.status is VerificationStatus.REJECTED_AGGREGATOR
    assert result.reason is not None and "not aligned" in result.reason


@pytest.mark.unit
def test_evaluate_feed_rejects_aggregator_over_threshold():
    links = ["https://fda.gov/1"] + [f"https://reuters.com/{i}" for i in range(5)]
    result = evaluate_feed(canonical_domain="fda.gov", feed_url="https://fda.gov/rss.xml", item_links=links)
    assert result.status is VerificationStatus.REJECTED_AGGREGATOR
    assert result.outbound_third_party_ratio > 0.05


@pytest.mark.unit
def test_evaluate_feed_rejects_third_party_redirect():
    result = evaluate_feed(
        canonical_domain="fda.gov",
        feed_url="https://fda.gov/rss.xml",
        item_links=[],
        redirect_urls=["https://fda.gov/feed", "https://aggregator.example/x"],
    )
    assert result.status is VerificationStatus.REJECTED_AGGREGATOR
    assert result.reason is not None and "redirect" in result.reason
