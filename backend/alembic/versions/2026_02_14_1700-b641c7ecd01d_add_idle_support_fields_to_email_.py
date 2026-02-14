"""add idle support fields to email_accounts

Revision ID: b641c7ecd01d
Revises: 9cc36a87ec5f
Create Date: 2026-02-14 17:00:17.027542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b641c7ecd01d"
down_revision: Union[str, Sequence[str], None] = "9cc36a87ec5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "email_accounts",
        sa.Column("use_polling", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "email_accounts",
        sa.Column("idle_supported", sa.Boolean(), nullable=True),
    )
    op.alter_column(
        "email_accounts",
        "polling_interval_sec",
        existing_type=sa.Integer(),
        server_default=sa.text("300"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "email_accounts",
        "polling_interval_sec",
        existing_type=sa.Integer(),
        server_default=sa.text("120"),
    )
    op.drop_column("email_accounts", "idle_supported")
    op.drop_column("email_accounts", "use_polling")
