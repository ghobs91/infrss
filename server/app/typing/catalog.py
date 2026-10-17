"""Primary-source catalog schemas."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import CatalogFeedType, EntityType, FeedCategory, VerificationStatus
from app.typing.common import response_config


class PrimaryEntityCreate(BaseModel):
    """Input for registering an authoritative organisation."""

    name: str
    entity_type: EntityType
    canonical_domain: str
    cik: str | None = None
    jurisdiction: str | None = None
    category: FeedCategory | None = None
    # Extra hosts the gatekeeper treats as this entity's own (company-owned alternate domains).
    feed_hosts: list[str] = Field(default_factory=list)


class PrimaryEntityRead(PrimaryEntityCreate):
    """Read model for a primary entity."""

    model_config = response_config

    id: UUID
    created_at: datetime


class CatalogFeedCreate(BaseModel):
    """Input for registering a candidate feed under an entity."""

    entity_id: UUID
    feed_url: str
    feed_type: CatalogFeedType


class CatalogFeedRead(CatalogFeedCreate):
    """Read model for a catalog feed and its verification state."""

    model_config = response_config

    id: UUID
    verification_status: VerificationStatus
    rejection_reason: str | None = None
    outbound_third_party_ratio: float | None = None
    failure_count: int = 0
    last_polled_at: datetime | None = None
    next_poll_at: datetime | None = None
    created_at: datetime


class CatalogSourceRead(BaseModel):
    """A browsable primary source: an entity together with its verified feeds.

    This is the discover-style view of the catalog - one row per organisation, grouped
    client-side by ``category``, so a single request renders the whole source list.
    """

    model_config = response_config

    id: UUID
    name: str
    entity_type: EntityType
    canonical_domain: str
    category: FeedCategory | None = None
    jurisdiction: str | None = None
    feeds: list[CatalogFeedRead] = []


@dataclass(frozen=True)
class GatekeeperResult:
    """Verdict of the primary-source gatekeeper for one candidate feed."""

    status: VerificationStatus
    reason: str | None = None
    outbound_third_party_ratio: float = 0.0

    @property
    def is_primary(self) -> bool:
        """True when the feed passed every gate."""
        return self.status is VerificationStatus.VERIFIED_PRIMARY
