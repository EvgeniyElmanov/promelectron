"""change product price to numeric 10 2

Revision ID: 8965b510122d
Revises: 85cc0efc25c6
Create Date: 2026-07-13 17:28:56.477366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8965b510122d'
down_revision: Union[str, Sequence[str], None] = '85cc0efc25c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change products.price from Float to Numeric(10, 2)."""
    op.alter_column(
        'products',
        'price',
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        type_=sa.Numeric(precision=10, scale=2),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert products.price to Float."""
    op.alter_column(
        'products',
        'price',
        existing_type=sa.Numeric(precision=10, scale=2),
        type_=sa.DOUBLE_PRECISION(precision=53),
        existing_nullable=False,
    )
