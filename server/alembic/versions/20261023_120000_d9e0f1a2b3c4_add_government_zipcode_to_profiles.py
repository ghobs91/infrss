"""add government zipcode to profiles

Stores the optional US ZIP code used to curate the government section of the primary-source
catalog (federal + the user's state + local sources).

Revision ID: d9e0f1a2b3c4
Revises: f3a4b5c6d7e8
Create Date: 2026-10-23 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9e0f1a2b3c4"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "profiles",
        sa.Column("government_zipcode", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("profiles", "government_zipcode")
