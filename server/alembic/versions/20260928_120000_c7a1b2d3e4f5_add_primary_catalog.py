"""add primary_entities and catalog_feeds

Revision ID: c7a1b2d3e4f5
Revises: 9b2e4d6f1a37
Create Date: 2026-09-28 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7a1b2d3e4f5"
down_revision: str | None = "9b2e4d6f1a37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE TYPE public.entitytype AS ENUM "
        "('GOV_FEDERAL', 'GOV_STATE', 'CORP_PUBLIC', 'CORP_PRIVATE', 'RESEARCH_ACADEMIC');"
    )
    op.execute("CREATE TYPE public.catalogfeedtype AS ENUM ('NATIVE_RSS', 'NATIVE_ATOM', 'SYNTHETIC_HTML');")
    op.execute(
        "CREATE TYPE public.verificationstatus AS ENUM "
        "('VERIFIED_PRIMARY', 'PENDING', 'REJECTED_AGGREGATOR', 'QUARANTINED');"
    )

    op.create_table(
        "primary_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "entity_type",
            postgresql.ENUM(
                "GOV_FEDERAL",
                "GOV_STATE",
                "CORP_PUBLIC",
                "CORP_PRIVATE",
                "RESEARCH_ACADEMIC",
                name="entitytype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("canonical_domain", sa.Text(), nullable=False),
        sa.Column("cik", sa.String(length=10), nullable=True),
        sa.Column("jurisdiction", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_primary_entities_canonical_domain"), "primary_entities", ["canonical_domain"], unique=True)

    op.create_table(
        "catalog_feeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=False),
        sa.Column(
            "feed_type",
            postgresql.ENUM("NATIVE_RSS", "NATIVE_ATOM", "SYNTHETIC_HTML", name="catalogfeedtype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "verification_status",
            postgresql.ENUM(
                "VERIFIED_PRIMARY",
                "PENDING",
                "REJECTED_AGGREGATOR",
                "QUARANTINED",
                name="verificationstatus",
                create_type=False,
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("outbound_third_party_ratio", sa.Float(), nullable=True),
        sa.Column("etag_header", sa.Text(), nullable=True),
        sa.Column("last_modified_header", sa.Text(), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_poll_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["primary_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catalog_feeds_entity_id"), "catalog_feeds", ["entity_id"], unique=False)
    op.create_index(op.f("ix_catalog_feeds_feed_url"), "catalog_feeds", ["feed_url"], unique=True)
    op.create_index(op.f("ix_catalog_feeds_next_poll_at"), "catalog_feeds", ["next_poll_at"], unique=False)

    # Match the security posture of 9b2e4d6f1a37_enable_rls: deny anon/authenticated PostgREST
    # access. The backend (table owner) and service-role webhooks bypass RLS unchanged.
    op.execute("ALTER TABLE public.primary_entities ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.catalog_feeds ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("catalog_feeds")
    op.drop_table("primary_entities")
    op.execute("DROP TYPE IF EXISTS public.verificationstatus;")
    op.execute("DROP TYPE IF EXISTS public.catalogfeedtype;")
    op.execute("DROP TYPE IF EXISTS public.entitytype;")
