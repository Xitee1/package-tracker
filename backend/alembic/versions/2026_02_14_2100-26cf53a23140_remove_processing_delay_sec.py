"""remove processing_delay_sec from imap_settings and watched_folders

Revision ID: 26cf53a23140
Revises: b641c7ecd01d
Create Date: 2026-02-14 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "26cf53a23140"
down_revision: Union[str, Sequence[str], None] = "b641c7ecd01d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove obsolete processing_delay_sec columns."""
    op.drop_column("imap_settings", "processing_delay_sec")
    op.drop_column("watched_folders", "processing_delay_sec")


def downgrade() -> None:
    """Re-add processing_delay_sec columns."""
    op.add_column(
        "watched_folders",
        sa.Column("processing_delay_sec", sa.Float(), nullable=True),
    )
    op.add_column(
        "imap_settings",
        sa.Column("processing_delay_sec", sa.Float(), nullable=False, server_default=sa.text("2.0")),
    )
