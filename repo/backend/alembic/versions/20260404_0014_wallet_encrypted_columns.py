"""convert wallet monetary columns to varchar for encrypted at-rest storage

Revision ID: 20260404_0014
Revises: 20260404_0013
Create Date: 2026-04-04 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260404_0014"
down_revision: str | None = "20260404_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Convert wallet balance from numeric to varchar to support encrypted ciphertext storage.
    op.alter_column(
        "wallet_accounts",
        "balance",
        type_=sa.String(255),
        existing_type=sa.Numeric(14, 2),
        postgresql_using="balance::text",
    )

    # Convert wallet ledger amount and balance_after to varchar.
    op.alter_column(
        "wallet_ledger",
        "amount",
        type_=sa.String(255),
        existing_type=sa.Numeric(14, 2),
        postgresql_using="amount::text",
    )
    op.alter_column(
        "wallet_ledger",
        "balance_after",
        type_=sa.String(255),
        existing_type=sa.Numeric(14, 2),
        postgresql_using="balance_after::text",
    )

    # Convert points_ledger pre_tax_amount to varchar.
    op.alter_column(
        "points_ledger",
        "pre_tax_amount",
        type_=sa.String(255),
        existing_type=sa.Numeric(12, 2),
        nullable=True,
        postgresql_using="pre_tax_amount::text",
    )


def downgrade() -> None:
    op.alter_column(
        "points_ledger",
        "pre_tax_amount",
        type_=sa.Numeric(12, 2),
        existing_type=sa.String(255),
        nullable=True,
        postgresql_using="pre_tax_amount::numeric(12,2)",
    )
    op.alter_column(
        "wallet_ledger",
        "balance_after",
        type_=sa.Numeric(14, 2),
        existing_type=sa.String(255),
        postgresql_using="balance_after::numeric(14,2)",
    )
    op.alter_column(
        "wallet_ledger",
        "amount",
        type_=sa.Numeric(14, 2),
        existing_type=sa.String(255),
        postgresql_using="amount::numeric(14,2)",
    )
    op.alter_column(
        "wallet_accounts",
        "balance",
        type_=sa.Numeric(14, 2),
        existing_type=sa.String(255),
        postgresql_using="balance::numeric(14,2)",
    )
