"""add store_id to audit_log for store-scoped filtering

Revision ID: 20260404_0013
Revises: 20260403_0012
Create Date: 2026-04-04 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260404_0013"
down_revision: str | None = "20260403_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("store_id", sa.Integer(), nullable=True))
    op.create_index("ix_audit_log_store_id", "audit_log", ["store_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_store_id", table_name="audit_log")
    op.drop_column("audit_log", "store_id")
