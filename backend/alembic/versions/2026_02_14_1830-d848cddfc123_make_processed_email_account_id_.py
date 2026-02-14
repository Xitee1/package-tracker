"""make processed_email account_id nullable and add source column

Revision ID: d848cddfc123
Revises: 47052895e669
Create Date: 2026-02-14 18:30:03.585542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd848cddfc123'
down_revision: Union[str, Sequence[str], None] = '47052895e669'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('processed_emails', sa.Column('source', sa.String(length=20), server_default='user_account', nullable=False))
    op.alter_column('processed_emails', 'account_id',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('processed_emails', 'account_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('processed_emails', 'source')
