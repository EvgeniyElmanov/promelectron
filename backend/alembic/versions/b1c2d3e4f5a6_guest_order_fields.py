"""guest order user_id nullable and guest fields

Revision ID: b1c2d3e4f5a6
Revises: 17116ba89cf4
Create Date: $(date -Iseconds)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '17116ba89cf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('orders', 'user_id',
                    existing_type=sa.Integer(),
                    nullable=True)
    op.add_column('orders', sa.Column('guest_email', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('guest_name', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('guest_phone', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders', 'guest_phone')
    op.drop_column('orders', 'guest_name')
    op.drop_column('orders', 'guest_email')
    op.alter_column('orders', 'user_id',
                    existing_type=sa.Integer(),
                    nullable=False)
