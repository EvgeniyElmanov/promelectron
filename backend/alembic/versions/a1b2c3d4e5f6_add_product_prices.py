"""add product_prices table, backfill from products.price, drop products.price

Revision ID: a1b2c3d4e5f6
Revises: 194ccff2a461
Create Date: 2026-08-24 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '194ccff2a461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'product_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('price_type', sa.String(length=64), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('onec_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'price_type', name='uq_product_prices_product_type'),
    )
    op.create_index(op.f('ix_product_prices_id'), 'product_prices', ['id'], unique=False)
    # Backfill: текущая products.price становится сайтовым видом цены.
    # Товары с price = 0 — «бесценные», строк в product_prices не получают.
    op.execute(
        "INSERT INTO product_prices (product_id, price_type, price, currency, onec_sync_at, created_at, updated_at) "
        "SELECT id, 'site', price, 'RUB', onec_sync_at, now(), now() FROM products WHERE price > 0"
    )
    op.drop_column('products', 'price')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('products', sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True))
    op.execute(
        "UPDATE products SET price = COALESCE("
        "(SELECT pp.price FROM product_prices pp WHERE pp.product_id = products.id AND pp.price_type = 'site'), 0)"
    )
    op.alter_column('products', 'price', nullable=False)
    op.drop_index(op.f('ix_product_prices_id'), table_name='product_prices')
    op.drop_table('product_prices')
