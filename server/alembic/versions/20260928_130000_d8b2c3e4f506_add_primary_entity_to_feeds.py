"""add primary_entity_id to feeds

Links a promoted global feed back to the primary entity it was catalogued under, so the reader
can mark it as a verified primary source.

Revision ID: d8b2c3e4f506
Revises: c7a1b2d3e4f5
Create Date: 2026-09-28 13:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8b2c3e4f506"
down_revision: str | None = "c7a1b2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("feeds", sa.Column("primary_entity_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_feeds_primary_entity_id",
        "feeds",
        "primary_entities",
        ["primary_entity_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_feeds_primary_entity_id"), "feeds", ["primary_entity_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_feeds_primary_entity_id"), table_name="feeds")
    op.drop_constraint("fk_feeds_primary_entity_id", "feeds", type_="foreignkey")
    op.drop_column("feeds", "primary_entity_id")
