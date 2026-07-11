"""add onec ids to products and categories

Revision ID: 00eea8e26e66
Revises: 48ee61411ed9
Create Date: 2026-07-11 06:30:21.117494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00eea8e26e66'
down_revision: Union[str, Sequence[str], None] = '48ee61411ed9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('products', sa.Column('onec_id', sa.String(length=36), nullable=True))
    op.add_column('products', sa.Column('onec_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_products_onec_id'), 'products', ['onec_id'], unique=True)

    op.add_column('categories', sa.Column('onec_id', sa.String(length=36), nullable=True))
    op.add_column('categories', sa.Column('onec_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('categories', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.create_index(op.f('ix_categories_onec_id'), 'categories', ['onec_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_categories_onec_id'), table_name='categories')
    op.drop_column('categories', 'onec_sync_at')
    op.drop_column('categories', 'onec_id')

    op.drop_index(op.f('ix_products_onec_id'), table_name='products')
    op.drop_column('products', 'onec_sync_at')
    op.drop_column('products', 'onec_id')
