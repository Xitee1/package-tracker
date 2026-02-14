"""add priority to module_config

Revision ID: 1751fdc3a36b
Revises: a3f1b2c4d5e6
Create Date: 2026-02-14 22:44:38.249083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1751fdc3a36b'
down_revision: Union[str, Sequence[str], None] = 'a3f1b2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add priority column to module_config."""
    op.add_column('module_config', sa.Column('priority', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Remove priority column from module_config."""
    op.drop_column('module_config', 'priority')
