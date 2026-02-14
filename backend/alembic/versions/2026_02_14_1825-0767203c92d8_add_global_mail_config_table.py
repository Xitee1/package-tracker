"""add global_mail_config table

Revision ID: 0767203c92d8
Revises: de6620fdd307
Create Date: 2026-02-14 18:25:16.261006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0767203c92d8'
down_revision: Union[str, Sequence[str], None] = 'de6620fdd307'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('global_mail_config',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('imap_host', sa.String(length=255), nullable=False),
    sa.Column('imap_port', sa.Integer(), nullable=False),
    sa.Column('imap_user', sa.String(length=255), nullable=False),
    sa.Column('imap_password_encrypted', sa.String(length=1024), nullable=False),
    sa.Column('use_ssl', sa.Boolean(), nullable=False),
    sa.Column('polling_interval_sec', sa.Integer(), nullable=False),
    sa.Column('use_polling', sa.Boolean(), nullable=False),
    sa.Column('idle_supported', sa.Boolean(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('watched_folder_path', sa.String(length=512), nullable=False),
    sa.Column('last_seen_uid', sa.Integer(), nullable=False),
    sa.Column('uidvalidity', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('global_mail_config')
