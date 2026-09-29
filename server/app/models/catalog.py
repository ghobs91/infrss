"""Primary-source catalog models - pure SQLAlchemy.

Two tables back the catalog engine:

* :class:`PrimaryEntity` - an authoritative organisation (agency, SEC filer, institution).
* :class:`CatalogFeed` - a candidate feed under verification. Kept separate from the global
  ``feeds`` table: a catalog feed is invisible to users until they explicitly subscribe to it,
  at which point it is promoted into ``feeds``. Owning its own fetch lifecycle lets verification
  poll independently of the subscriber-gated article refresh in ``feeds``.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.enums import CatalogFeedType, EntityType, VerificationStatus


class PrimaryEntity(Base):
    """An authoritative organisation whose own disclosures are the primary source."""

    __tablename__ = "primary_entities"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(Text, nullable=False)
    entity_type = Column(
        SQLEnum(EntityType, name="entitytype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    canonical_domain = Column(Text, nullable=False, unique=True, index=True)
    cik = Column(String(10), nullable=True)  # Zero-padded 10-digit SEC CIK for filers
    jurisdiction = Column(String(10), nullable=True)  # ISO 3166-1 / 3166-2 code
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    catalog_feeds = relationship("CatalogFeed", back_populates="entity", cascade="all, delete-orphan")


class CatalogFeed(Base):
    """A candidate native or synthetic feed awaiting/after gatekeeper verification."""

    __tablename__ = "catalog_feeds"

    id = Column(SQLUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    entity_id = Column(
        SQLUUID(as_uuid=True),
        ForeignKey("primary_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feed_url = Column(Text, nullable=False, unique=True, index=True)
    feed_type = Column(
        SQLEnum(CatalogFeedType, name="catalogfeedtype", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    verification_status = Column(
        SQLEnum(VerificationStatus, name="verificationstatus", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=VerificationStatus.PENDING.value,
        default=VerificationStatus.PENDING,
    )
    rejection_reason = Column(Text, nullable=True)
    outbound_third_party_ratio = Column(Float, nullable=True)

    # Conditional-GET lifecycle (mirrors feeds.*), owned here so verification polling does not
    # depend on the subscriber-gated refresh in the global feeds table.
    etag_header = Column(Text, nullable=True)
    last_modified_header = Column(Text, nullable=True)
    failure_count = Column(Integer, nullable=False, server_default="0", default=0)
    last_polled_at = Column(DateTime(timezone=True), nullable=True)
    next_poll_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_updated_at = Column(DateTime(timezone=True), nullable=True)

    entity = relationship("PrimaryEntity", back_populates="catalog_feeds")
