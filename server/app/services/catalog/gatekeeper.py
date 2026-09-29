"""Gatekeeper engine: enforce that a catalog feed is a genuine primary source.

Pure, side-effect-free rules (no database, no network) so they can be unit tested directly and
reused by both the catalog worker and the subscribe flow. "Primary source" is enforced on three
axes: the feed must be hosted on the entity's own domain, must not be a link-out aggregator, and
must not redirect to a third-party origin.
"""

from collections.abc import Sequence
from urllib.parse import urlparse

from app.core.constants import CATALOG_ALLOWED_FEED_HOSTS, CATALOG_OUTBOUND_THIRD_PARTY_RATIO
from app.models.enums import VerificationStatus
from app.typing.catalog import GatekeeperResult

ALLOWED_FEED_HOSTS = CATALOG_ALLOWED_FEED_HOSTS


def domain_from_url(url: str) -> str:
    """Return the lower-cased hostname of ``url``, or an empty string when unparseable."""
    if not url:
        return ""
    try:
        return (urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def canonical_domain_from_url(url: str) -> str:
    """Hostname to store as an entity's canonical domain: lowercased, portless, no leading ``www.``."""
    host = domain_from_url(url)
    return host[4:] if host.startswith("www.") else host


def is_domain_aligned(
    host: str,
    canonical_domain: str,
    allowed_hosts: Sequence[str] = ALLOWED_FEED_HOSTS,
) -> bool:
    """True when ``host`` is the canonical domain, a subdomain of it, or an allowed feed host.

    Only the feed side may be a subdomain: ``news.microsoft.com`` is aligned with
    ``microsoft.com``, but ``microsoft.com`` is not aligned with ``news.microsoft.com``.
    """
    host = (host or "").lower().rstrip(".")
    canonical_domain = (canonical_domain or "").lower().rstrip(".")
    if not host or not canonical_domain:
        return False
    if host == canonical_domain or host.endswith(f".{canonical_domain}"):
        return True
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in allowed_hosts)


def outbound_third_party_ratio(item_links: Sequence[str], canonical_domain: str) -> float:
    """Fraction of item links that leave the entity's own domain (0.0 when there are none)."""
    links = [link for link in item_links if link]
    if not links:
        return 0.0
    off_domain = sum(1 for link in links if not is_domain_aligned(domain_from_url(link), canonical_domain))
    return off_domain / len(links)


def redirect_chain_is_authorized(redirect_urls: Sequence[str], canonical_domain: str) -> bool:
    """True when every redirect hop stays on the entity's own (or an allowed) domain."""
    return all(is_domain_aligned(domain_from_url(url), canonical_domain) for url in redirect_urls)


def evaluate_feed(
    *,
    canonical_domain: str,
    feed_url: str,
    item_links: Sequence[str],
    redirect_urls: Sequence[str] = (),
) -> GatekeeperResult:
    """Apply every gate and return the resulting :class:`GatekeeperResult`.

    Args:
        canonical_domain: The entity's own domain the feed must belong to.
        feed_url: The candidate feed's URL.
        item_links: Item ``<link>``/``<guid>`` targets from a sample of the feed.
        redirect_urls: Every hop the fetch followed, in order (excluding the origin).
    """
    feed_host = domain_from_url(feed_url)
    if not is_domain_aligned(feed_host, canonical_domain):
        return GatekeeperResult(
            status=VerificationStatus.REJECTED_AGGREGATOR,
            reason=f"feed host {feed_host!r} is not aligned with {canonical_domain!r}",
        )

    if redirect_urls and not redirect_chain_is_authorized(redirect_urls, canonical_domain):
        return GatekeeperResult(
            status=VerificationStatus.REJECTED_AGGREGATOR,
            reason="feed redirects through a third-party origin",
        )

    ratio = outbound_third_party_ratio(item_links, canonical_domain)
    if ratio > CATALOG_OUTBOUND_THIRD_PARTY_RATIO:
        return GatekeeperResult(
            status=VerificationStatus.REJECTED_AGGREGATOR,
            reason=(f"{ratio:.1%} of items link off-domain (limit {CATALOG_OUTBOUND_THIRD_PARTY_RATIO:.0%})"),
            outbound_third_party_ratio=ratio,
        )

    return GatekeeperResult(status=VerificationStatus.VERIFIED_PRIMARY, outbound_third_party_ratio=ratio)
