"""add article_layman_summaries

Stores structured plain-language summaries keyed by the shared article_contents row, so one
generated summary serves every user who reads the same primary-source document.

Revision ID: e9c3d4f5a6b7
Revises: d8b2c3e4f506
Create Date: 2026-09-28 14:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9c3d4f5a6b7"
down_revision: str | None = "d8b2c3e4f506"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "article_layman_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("what_happened", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("key_impact", sa.Text(), nullable=False),
        sa.Column("model_identifier", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["article_contents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_article_layman_summaries_content_id"),
        "article_layman_summaries",
        ["content_id"],
        unique=True,
    )
    op.execute("ALTER TABLE public.article_layman_summaries ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("article_layman_summaries")
