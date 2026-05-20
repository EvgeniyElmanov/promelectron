"""add tracking_number to orders

Revision ID: 4a2e8c9d1f00
Revises: f30bc44684ed
Create Date: 2026-05-19 15:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a2e8c9d1f00'
down_revision: Union[str, Sequence[str], None] = 'f30bc44684ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('orders', sa.Column('tracking_number', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders', 'tracking_number')
