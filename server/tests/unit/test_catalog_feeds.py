"""Unit tests for catalog feed URL helpers (pure, no database)."""

import pytest

from app.crud.catalog.feeds import url_host_variants


@pytest.mark.unit
def test_url_host_variants_pairs_www_and_apex():
    assert set(url_host_variants("https://audi.com/en/feeds/press-releases")) == {
        "https://audi.com/en/feeds/press-releases",
        "https://www.audi.com/en/feeds/press-releases",
    }
    assert set(url_host_variants("https://www.press.bmwgroup.com/global/rss/topic/803")) == {
        "https://www.press.bmwgroup.com/global/rss/topic/803",
        "https://press.bmwgroup.com/global/rss/topic/803",
    }


@pytest.mark.unit
def test_url_host_variants_ignores_non_http_urls():
    assert url_host_variants("rsshub://example/feed") == ["rsshub://example/feed"]
    assert url_host_variants("newsletter://token/user@example.com") == ["newsletter://token/user@example.com"]
