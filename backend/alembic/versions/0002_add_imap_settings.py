"""add imap settings and watched folder overrides

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "imap_settings" not in inspector.get_table_names():
        op.create_table(
            "imap_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("max_email_age_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("processing_delay_sec", sa.Float(), nullable=False, server_default="2.0"),
            sa.Column(
                "check_uidvalidity",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )

    existing_columns = {c["name"] for c in inspector.get_columns("watched_folders")}

    if "max_email_age_days" not in existing_columns:
        op.add_column(
            "watched_folders", sa.Column("max_email_age_days", sa.Integer(), nullable=True)
        )
    if "processing_delay_sec" not in existing_columns:
        op.add_column(
            "watched_folders", sa.Column("processing_delay_sec", sa.Float(), nullable=True)
        )
    if "uidvalidity" not in existing_columns:
        op.add_column("watched_folders", sa.Column("uidvalidity", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("watched_folders", "uidvalidity")
    op.drop_column("watched_folders", "processing_delay_sec")
    op.drop_column("watched_folders", "max_email_age_days")

    op.drop_table("imap_settings")
