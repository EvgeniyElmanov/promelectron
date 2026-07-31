"""add attribute tables

Revision ID: 194ccff2a461
Revises: 937fc6751168
Create Date: 2026-07-31 04:09:33.822937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '194ccff2a461'
down_revision: Union[str, Sequence[str], None] = '937fc6751168'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('attributes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('value_type', sa.Enum('number', 'enum', 'bool', 'string', name='attributevaluetype'), nullable=False),
    sa.Column('unit', sa.String(), nullable=True),
    sa.Column('is_filterable', sa.Boolean(), nullable=False),
    sa.Column('sort', sa.Integer(), nullable=False),
    sa.Column('onec_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attributes_code'), 'attributes', ['code'], unique=True)
    op.create_index(op.f('ix_attributes_onec_id'), 'attributes', ['onec_id'], unique=True)
    op.create_table('product_attribute_values',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('attribute_id', sa.Integer(), nullable=False),
    sa.Column('value_number', sa.Numeric(precision=18, scale=6), nullable=True),
    sa.Column('value_text', sa.String(), nullable=True),
    sa.Column('value_bool', sa.Boolean(), nullable=True),
    sa.Column('option_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('product_id', 'attribute_id', name='uq_product_attribute')
    )
    op.create_index(op.f('ix_product_attribute_values_attribute_id'), 'product_attribute_values', ['attribute_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_product_attribute_values_attribute_id'), table_name='product_attribute_values')
    op.drop_table('product_attribute_values')
    op.drop_index(op.f('ix_attributes_onec_id'), table_name='attributes')
    op.drop_index(op.f('ix_attributes_code'), table_name='attributes')
    op.drop_table('attributes')
    sa.Enum(name='attributevaluetype').drop(op.get_bind(), checkfirst=True)
