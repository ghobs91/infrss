"""clamp future feed_article published_at values

Revision ID: b1c2d3e4f5a6
Revises: d9e0f1a2b3c4
Create Date: 2026-11-08 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "d9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace future publication dates with the ingest time.

    Some feeds publish placeholder dates years ahead (Brave Research stamps entries with
    the venue year). Because article lists sort by ``published_at DESC``, those rows sit
    above every real article forever. Collapse them to when they were ingested; new rows
    are clamped at parse time.
    """
    op.execute("UPDATE feed_articles SET published_at = created_at WHERE published_at > now()")


def downgrade() -> None:
    # The original future dates are not recoverable; clamping is the intended end state.
    pass
