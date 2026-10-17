"""add feed_hosts to primary_entities

Adds a per-entity list of extra hosts the gatekeeper treats as the entity's own, so a
company's blog/newsroom on an alternate domain it owns (github.blog, shopify.engineering,
engineering.fb.com, ...) is accepted without loosening the global CDN allowlist.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-10-17 13:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("primary_entities", sa.Column("feed_hosts", postgresql.ARRAY(sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("primary_entities", "feed_hosts")
