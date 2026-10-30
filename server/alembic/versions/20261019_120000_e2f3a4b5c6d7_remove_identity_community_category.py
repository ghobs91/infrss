"""remove identity_community category and the ADL source

Drops the ``identity_community`` value from the ``feedcategory`` enum (recreating the type,
since Postgres cannot drop enum values in place), reassigns catalog entities that used it to
``society_law_history``, and deletes the blocked Anti-Defamation League entity (its catalog
feeds cascade via the foreign key).

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-10-19 12:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# feedcategory values with ``identity_community`` removed.
_ENUM_VALUES = (
    "arts_culture",
    "automotive_transport",
    "business_finance",
    "consumer_tech_digital",
    "entertainment",
    "family_relationships",
    "food_drink",
    "gaming",
    "health_wellness",
    "home_hobbies",
    "industry_professions",
    "news_current_events",
    "regional_local",
    "science_nature",
    "society_law_history",
    "software_engineering",
    "sports",
    "style_shopping",
    "travel_geography",
    "miscellaneous",
)

_ENUM_VALUES_WITH_IDENTITY = tuple(sorted((*_ENUM_VALUES, "identity_community")))


def _recreate_feedcategory_enum(values: tuple[str, ...]) -> None:
    """Rebuild the shared ``feedcategory`` type with exactly ``values`` (both columns detached)."""
    op.execute("ALTER TABLE feeds ALTER COLUMN top_level_category DROP DEFAULT")
    op.execute("ALTER TABLE feeds ALTER COLUMN top_level_category TYPE TEXT")
    op.execute("ALTER TABLE primary_entities ALTER COLUMN category TYPE TEXT")
    op.execute("DROP TYPE public.feedcategory")
    literal = ", ".join(f"'{value}'" for value in values)
    op.execute(f"CREATE TYPE public.feedcategory AS ENUM ({literal})")
    op.execute(
        "ALTER TABLE feeds ALTER COLUMN top_level_category TYPE public.feedcategory "
        "USING top_level_category::public.feedcategory"
    )
    op.execute(
        "ALTER TABLE primary_entities ALTER COLUMN category TYPE public.feedcategory "
        "USING category::public.feedcategory"
    )
    op.execute("ALTER TABLE feeds ALTER COLUMN top_level_category SET DEFAULT 'miscellaneous'::public.feedcategory")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE primary_entities SET category='society_law_history' WHERE category='identity_community'")
    op.execute("DELETE FROM primary_entities WHERE canonical_domain='adl.org'")
    _recreate_feedcategory_enum(_ENUM_VALUES)


def downgrade() -> None:
    """Downgrade schema."""
    _recreate_feedcategory_enum(_ENUM_VALUES_WITH_IDENTITY)
