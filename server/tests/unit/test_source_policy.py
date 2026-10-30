"""Unit tests for the editorial source blocklist (pure, no database)."""

import pytest

from app.utils.source_policy import BLOCKED_SOURCE_DOMAINS, is_blocked_source


@pytest.mark.unit
def test_blocked_domains_and_their_subdomains_are_blocked():
    assert BLOCKED_SOURCE_DOMAINS
    for domain in BLOCKED_SOURCE_DOMAINS:
        assert is_blocked_source(domain)
        assert is_blocked_source(f"www.{domain}")
        assert is_blocked_source(f"press.{domain}")


@pytest.mark.unit
def test_unrelated_domains_are_not_blocked():
    assert not is_blocked_source("example.com")
    assert not is_blocked_source("fda.gov")
    assert not is_blocked_source("")
    # A shared suffix is not enough: the match must be on a domain boundary.
    assert not is_blocked_source("notadl.org")
