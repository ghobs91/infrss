"""add catalog_feed_id to feeds

Records which catalog feed a promoted global feed came from, so the catalog can mark a source as
already subscribed reliably: the promoted feed's stored ``url`` is the redirect-resolved URL and
can differ from the catalog feed's URL (e.g. ``tsa.gov`` -> ``www.tsa.gov``).

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-10-19 13:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("feeds", sa.Column("catalog_feed_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_feeds_catalog_feed_id",
        "feeds",
        "catalog_feeds",
        ["catalog_feed_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_feeds_catalog_feed_id"), "feeds", ["catalog_feed_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_feeds_catalog_feed_id"), table_name="feeds")
    op.drop_constraint("fk_feeds_catalog_feed_id", "feeds", type_="foreignkey")
    op.drop_column("feeds", "catalog_feed_id")
