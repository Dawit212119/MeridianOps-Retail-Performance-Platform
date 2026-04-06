"""change quiz_topics uniqueness from global code to (store_id, code)

Revision ID: 20260406_0015
Revises: 20260404_0014
Create Date: 2026-04-06 08:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260406_0015"
down_revision: str | None = "20260404_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Migration 0004 created the unique constraint via sa.UniqueConstraint("code")
# without an explicit name.  PostgreSQL auto-generates this as
# "{table}_{column}_key" -> "quiz_topics_code_key".
_PG_AUTO_CONSTRAINT = "quiz_topics_code_key"


def upgrade() -> None:
    # Drop the old global unique index and constraint on code.
    op.drop_index("ix_quiz_topics_code", table_name="quiz_topics")
    op.drop_constraint(_PG_AUTO_CONSTRAINT, table_name="quiz_topics", type_="unique")

    # Re-create a non-unique index on code for lookups.
    op.create_index("ix_quiz_topics_code", "quiz_topics", ["code"], unique=False)

    # Create the new composite unique constraint (store_id, code).
    op.create_unique_constraint("uq_quiz_topics_store_code", "quiz_topics", ["store_id", "code"])


def downgrade() -> None:
    op.drop_constraint("uq_quiz_topics_store_code", table_name="quiz_topics", type_="unique")
    op.drop_index("ix_quiz_topics_code", table_name="quiz_topics")
    op.create_index("ix_quiz_topics_code", "quiz_topics", ["code"], unique=True)
    op.create_unique_constraint(_PG_AUTO_CONSTRAINT, "quiz_topics", ["code"])
