"""add store_ids_json to kpi_job_runs for object-level scoping

Revision ID: 20260406_0016
Revises: 20260406_0015
Create Date: 2026-04-06 08:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260406_0016"
down_revision: str | None = "20260406_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("kpi_job_runs", sa.Column("store_ids_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("kpi_job_runs", "store_ids_json")
