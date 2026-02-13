"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    conn = op.get_bind()
    return name in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(255), unique=True, index=True, nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column(
                "is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if not _table_exists("email_accounts"):
        op.create_table(
            "email_accounts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("imap_host", sa.String(255), nullable=False),
            sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
            sa.Column("imap_user", sa.String(255), nullable=False),
            sa.Column("imap_password_encrypted", sa.String(1024), nullable=False),
            sa.Column("use_ssl", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "polling_interval_sec", sa.Integer(), nullable=False, server_default="120"
            ),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if not _table_exists("watched_folders"):
        op.create_table(
            "watched_folders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "account_id",
                sa.Integer(),
                sa.ForeignKey("email_accounts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("folder_path", sa.String(512), nullable=False),
            sa.Column("last_seen_uid", sa.Integer(), nullable=False, server_default="0"),
        )

    if not _table_exists("orders"):
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("order_number", sa.String(255), nullable=True, index=True),
            sa.Column("tracking_number", sa.String(255), nullable=True, index=True),
            sa.Column("carrier", sa.String(255), nullable=True),
            sa.Column("vendor_name", sa.String(255), nullable=True),
            sa.Column("vendor_domain", sa.String(255), nullable=True),
            sa.Column("status", sa.String(50), nullable=False, server_default="ordered"),
            sa.Column("order_date", sa.Date(), nullable=True),
            sa.Column("total_amount", sa.Numeric(10, 2), nullable=True),
            sa.Column("currency", sa.String(10), nullable=True),
            sa.Column("items", sa.JSON(), nullable=True),
            sa.Column("estimated_delivery", sa.Date(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )

    if not _table_exists("order_events"):
        op.create_table(
            "order_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "order_id",
                sa.Integer(),
                sa.ForeignKey("orders.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("old_status", sa.String(50), nullable=True),
            sa.Column("new_status", sa.String(50), nullable=False),
            sa.Column("source_email_message_id", sa.String(512), nullable=True),
            sa.Column("source_email_uid", sa.Integer(), nullable=True),
            sa.Column("source_folder", sa.String(512), nullable=True),
            sa.Column("source_account_id", sa.Integer(), nullable=True),
            sa.Column("llm_raw_response", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    if not _table_exists("llm_configs"):
        op.create_table(
            "llm_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model_name", sa.String(255), nullable=False),
            sa.Column(
                "api_key_encrypted", sa.String(1024), nullable=False, server_default=""
            ),
            sa.Column("api_base_url", sa.String(512), nullable=False, server_default=""),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
            ),
        )

    if not _table_exists("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("key_hash", sa.String(64), unique=True, index=True, nullable=False),
            sa.Column("key_prefix", sa.String(12), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("llm_configs")
    op.drop_table("order_events")
    op.drop_table("orders")
    op.drop_table("watched_folders")
    op.drop_table("email_accounts")
    op.drop_table("users")
