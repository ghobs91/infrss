"""add sector to primary_entities

Adds a nullable subcategory to catalog entities so large sections can be split client-side
(the government section groups by sector: transit, health, commerce, transportation, ...).
Entities without a stored value fall back to a name/domain heuristic in the catalog API.

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-10-18 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("primary_entities", sa.Column("sector", sa.String(length=32), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("primary_entities", "sector")
