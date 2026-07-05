"""add_cart_item_selected

Revision ID: 9614c59dd5a3
Revises: b3edea26617e
Create Date: 2026-07-04 05:12:34.534671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9614c59dd5a3'
down_revision: Union[str, Sequence[str], None] = 'b3edea26617e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'cart_items',
        sa.Column('selected', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('cart_items', 'selected')
