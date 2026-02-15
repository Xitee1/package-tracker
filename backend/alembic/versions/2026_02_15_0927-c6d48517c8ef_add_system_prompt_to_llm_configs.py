"""add system_prompt to llm_configs

Revision ID: c6d48517c8ef
Revises: 1751fdc3a36b
Create Date: 2026-02-15 09:27:19.027170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c6d48517c8ef'
down_revision: Union[str, Sequence[str], None] = '1751fdc3a36b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('llm_configs', sa.Column('system_prompt', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('llm_configs', 'system_prompt')
