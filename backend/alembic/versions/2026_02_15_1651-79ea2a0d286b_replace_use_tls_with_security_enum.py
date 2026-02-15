"""replace use_tls with security enum

Revision ID: 79ea2a0d286b
Revises: 5a68850d4cc1
Create Date: 2026-02-15 16:51:18.391111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79ea2a0d286b'
down_revision: Union[str, Sequence[str], None] = '5a68850d4cc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace use_tls boolean with security enum string."""
    op.add_column('smtp_config', sa.Column('security', sa.String(10), nullable=True))
    # Migrate existing data: use_tls=True -> 'tls', use_tls=False -> 'none'
    op.execute("UPDATE smtp_config SET security = CASE WHEN use_tls THEN 'tls' ELSE 'none' END")
    op.alter_column('smtp_config', 'security', nullable=False, server_default='starttls')
    op.drop_column('smtp_config', 'use_tls')


def downgrade() -> None:
    """Restore use_tls boolean from security enum."""
    op.add_column('smtp_config', sa.Column('use_tls', sa.Boolean(), nullable=True))
    op.execute("UPDATE smtp_config SET use_tls = (security = 'tls')")
    op.alter_column('smtp_config', 'use_tls', nullable=False, server_default=sa.text('true'))
    op.drop_column('smtp_config', 'security')
