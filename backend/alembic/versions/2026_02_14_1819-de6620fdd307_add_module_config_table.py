"""add module_config table

Revision ID: de6620fdd307
Revises: 26cf53a23140
Create Date: 2026-02-14 18:19:17.959068

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'de6620fdd307'
down_revision: Union[str, Sequence[str], None] = '26cf53a23140'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('module_config',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('module_key', sa.String(length=50), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_module_config_module_key'), 'module_config', ['module_key'], unique=True)
    op.bulk_insert(
        sa.table(
            "module_config",
            sa.column("module_key", sa.String),
            sa.column("enabled", sa.Boolean),
        ),
        [
            {"module_key": "email-imap", "enabled": True},
            {"module_key": "email-global", "enabled": False},
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_module_config_module_key'), table_name='module_config')
    op.drop_table('module_config')
