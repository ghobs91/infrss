"""add category to primary_entities

Adds an industry/topic category to primary entities so the catalog browse view can group
sources (government, corporate, research) by category. The column reuses the existing
``feedcategory`` enum shared with ``feeds.top_level_category``.

Revision ID: b7c8d9e0f1a2
Revises: e9c3d4f5a6b7
Create Date: 2026-10-17 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "e9c3d4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ``create_type=False``: the feedcategory enum already exists (feeds.top_level_category).
    op.add_column(
        "primary_entities",
        sa.Column("category", postgresql.ENUM(name="feedcategory", create_type=False), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("primary_entities", "category")
