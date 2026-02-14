"""add user_sender_address table

Revision ID: 47052895e669
Revises: 0767203c92d8
Create Date: 2026-02-14 18:27:54.687745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '47052895e669'
down_revision: Union[str, Sequence[str], None] = '0767203c92d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_sender_address',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('email_address', sa.String(length=320), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sender_address_email_address'), 'user_sender_address', ['email_address'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_sender_address_email_address'), table_name='user_sender_address')
    op.drop_table('user_sender_address')
