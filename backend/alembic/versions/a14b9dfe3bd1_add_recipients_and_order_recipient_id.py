"""add_recipients_and_order_recipient_id

Revision ID: a14b9dfe3bd1
Revises: db0971c05386
Create Date: 2026-06-25 05:34:16.834056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a14b9dfe3bd1'
down_revision: Union[str, Sequence[str], None] = 'db0971c05386'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create recipients table
    op.create_table(
        'recipients',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('patronymic', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('country_code', sa.String(), nullable=False, server_default='RU'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_recipients_id'), 'recipients', ['id'], unique=False)
    op.create_index(op.f('ix_recipients_user_id'), 'recipients', ['user_id'], unique=False)

    # Add user profile fields
    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('patronymic', sa.String(), nullable=True))
    op.add_column('users', sa.Column('country_code', sa.String(), nullable=True, server_default='RU'))

    # Add orders.recipient_id
    op.add_column('orders', sa.Column('recipient_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_orders_recipient_id'), 'orders', ['recipient_id'], unique=False)
    op.create_foreign_key(
        'fk_orders_recipient_id',
        'orders',
        'recipients',
        ['recipient_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # Migrate existing orders to recipients (one recipient per order)
    op.execute("""
        DO $$
        DECLARE
            r_id INT;
            o RECORD;
        BEGIN
            FOR o IN SELECT id, user_id, guest_name, recipient_first_name, recipient_last_name, guest_phone FROM orders LOOP
                INSERT INTO recipients (
                    user_id,
                    first_name,
                    last_name,
                    patronymic,
                    phone,
                    country_code,
                    is_default,
                    created_at,
                    updated_at
                )
                VALUES (
                    o.user_id,
                    COALESCE(NULLIF(TRIM(o.recipient_first_name), ''), NULLIF(SPLIT_PART(o.guest_name, ' ', 1), ''), 'Получатель'),
                    COALESCE(NULLIF(TRIM(o.recipient_last_name), ''), NULLIF(SPLIT_PART(o.guest_name, ' ', 2), ''), ''),
                    NULL,
                    COALESCE(o.guest_phone, (SELECT phone FROM users WHERE id = o.user_id), '+70000000000'),
                    'RU',
                    FALSE,
                    NOW(),
                    NOW()
                )
                RETURNING id INTO r_id;

                UPDATE orders SET recipient_id = r_id WHERE id = o.id;
            END LOOP;
        END $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_orders_recipient_id', 'orders', type_='foreignkey')
    op.drop_index(op.f('ix_orders_recipient_id'), table_name='orders')
    op.drop_column('orders', 'recipient_id')

    op.drop_column('users', 'country_code')
    op.drop_column('users', 'patronymic')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')

    op.drop_index(op.f('ix_recipients_user_id'), table_name='recipients')
    op.drop_index(op.f('ix_recipients_id'), table_name='recipients')
    op.drop_table('recipients')
