"""drop is_active from global_mail_config

Revision ID: a3f1b2c4d5e6
Revises: d848cddfc123
Create Date: 2026-02-14 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3f1b2c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d848cddfc123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop is_active column from global_mail_config."""
    op.drop_column("global_mail_config", "is_active")


def downgrade() -> None:
    """Re-add is_active column to global_mail_config."""
    op.add_column(
        "global_mail_config",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
