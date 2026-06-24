"""cdek_orders_and_jobs

Revision ID: 9a1b2c3d4e5f
Revises: becdb9cce9b1
Create Date: 2026-06-24 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = 'becdb9cce9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create jobs, cdek_orders, cdek_status_history; migrate CDEK data."""
    # ### jobs ###
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('processing_log', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('run_after', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timeout', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_job_type'), 'jobs', ['job_type'], unique=False)
    op.create_index(op.f('ix_jobs_run_after'), 'jobs', ['run_after'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_index(op.f('ix_jobs_deadline'), 'jobs', ['deadline'], unique=False)

    # ### cdek_orders ###
    op.create_table(
        'cdek_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('tariff_code', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('delivery_mode', sa.String(), nullable=False, server_default='PVZ'),
        sa.Column('delivery_point', sa.String(), nullable=True),
        sa.Column('to_location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('from_location', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'),
        sa.Column('period_min', sa.Integer(), nullable=True),
        sa.Column('period_max', sa.Integer(), nullable=True),
        sa.Column('cdek_uuid', sa.String(), nullable=True),
        sa.Column('cdek_number', sa.String(), nullable=True),
        sa.Column('cdek_status', sa.String(), nullable=True),
        sa.Column('tracking_number', sa.String(), nullable=True),
        sa.Column('sync_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sync_failed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('order_id'),
        sa.UniqueConstraint('cdek_uuid')
    )
    op.create_index(op.f('ix_cdek_orders_order_id'), 'cdek_orders', ['order_id'], unique=False)
    op.create_index(op.f('ix_cdek_orders_cdek_uuid'), 'cdek_orders', ['cdek_uuid'], unique=False)
    op.create_index(op.f('ix_cdek_orders_cdek_number'), 'cdek_orders', ['cdek_number'], unique=False)
    op.create_index(op.f('ix_cdek_orders_cdek_status'), 'cdek_orders', ['cdek_status'], unique=False)

    # ### cdek_status_history ###
    op.create_table(
        'cdek_status_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cdek_order_id', sa.Integer(), nullable=False),
        sa.Column('cdek_status', sa.String(), nullable=False),
        sa.Column('status_date_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('city_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['cdek_order_id'], ['cdek_orders.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('cdek_order_id', 'cdek_status', 'status_date_time')
    )
    op.create_index(op.f('ix_cdek_status_history_cdek_order_id'), 'cdek_status_history', ['cdek_order_id'], unique=False)
    op.create_index(op.f('ix_cdek_status_history_cdek_status'), 'cdek_status_history', ['cdek_status'], unique=False)
    op.create_index(op.f('ix_cdek_status_history_status_date_time'), 'cdek_status_history', ['status_date_time'], unique=False)

    # ### Migrate data from orders to cdek_orders ###
    op.execute(
        """
        INSERT INTO cdek_orders (
            order_id, tariff_code, delivery_mode, delivery_point,
            to_location, from_location, price, period_min, period_max,
            cdek_uuid, cdek_number, cdek_status, tracking_number,
            sync_attempts, sync_failed, created_at, updated_at
        )
        SELECT
            id, cdek_tariff_code, cdek_delivery_mode, cdek_delivery_point,
            cdek_to_location, cdek_from_location, cdek_price, cdek_period_min, cdek_period_max,
            cdek_uuid, cdek_number, cdek_status, tracking_number,
            cdek_sync_attempts, cdek_sync_failed, created_at, updated_at
        FROM orders
        """
    )

    # ### Link orders to cdek_orders ###
    op.add_column('orders', sa.Column('cdek_order_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_orders_cdek_order_id'), 'orders', ['cdek_order_id'], unique=False)
    op.create_unique_constraint(op.f('uq_orders_cdek_order_id'), 'orders', ['cdek_order_id'])
    op.create_foreign_key(op.f('fk_orders_cdek_order_id_cdek_orders'), 'orders', 'cdek_orders', ['cdek_order_id'], ['id'], ondelete='SET NULL')

    op.execute(
        """
        UPDATE orders
        SET cdek_order_id = cdek_orders.id
        FROM cdek_orders
        WHERE cdek_orders.order_id = orders.id
        """
    )

    # ### Drop old CDEK columns from orders ###
    op.drop_column('orders', 'cdek_sync_failed')
    op.drop_column('orders', 'cdek_sync_attempts')
    op.drop_column('orders', 'cdek_status')
    op.drop_column('orders', 'cdek_number')
    op.drop_column('orders', 'cdek_uuid')
    op.drop_column('orders', 'cdek_period_max')
    op.drop_column('orders', 'cdek_period_min')
    op.drop_column('orders', 'cdek_price')
    op.drop_column('orders', 'cdek_from_location')
    op.drop_column('orders', 'cdek_to_location')
    op.drop_column('orders', 'cdek_delivery_point')
    op.drop_column('orders', 'cdek_delivery_mode')
    op.drop_column('orders', 'cdek_tariff_code')


def downgrade() -> None:
    """Downgrade schema."""
    # ### Restore old columns on orders ###
    op.add_column('orders', sa.Column('cdek_tariff_code', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('cdek_delivery_mode', sa.String(), nullable=False, server_default='PVZ'))
    op.add_column('orders', sa.Column('cdek_delivery_point', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('cdek_to_location', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('orders', sa.Column('cdek_from_location', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('orders', sa.Column('cdek_price', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.0'))
    op.add_column('orders', sa.Column('cdek_period_min', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('cdek_period_max', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('cdek_uuid', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('cdek_number', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('cdek_status', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('cdek_sync_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('orders', sa.Column('cdek_sync_failed', sa.Boolean(), nullable=False, server_default='false'))

    op.execute(
        """
        UPDATE orders
        SET
            cdek_tariff_code = cdek_orders.tariff_code,
            cdek_delivery_mode = cdek_orders.delivery_mode,
            cdek_delivery_point = cdek_orders.delivery_point,
            cdek_to_location = cdek_orders.to_location,
            cdek_from_location = cdek_orders.from_location,
            cdek_price = cdek_orders.price,
            cdek_period_min = cdek_orders.period_min,
            cdek_period_max = cdek_orders.period_max,
            cdek_uuid = cdek_orders.cdek_uuid,
            cdek_number = cdek_orders.cdek_number,
            cdek_status = cdek_orders.cdek_status,
            cdek_sync_attempts = cdek_orders.sync_attempts,
            cdek_sync_failed = cdek_orders.sync_failed
        FROM cdek_orders
        WHERE cdek_orders.order_id = orders.id
        """
    )

    op.drop_constraint(op.f('fk_orders_cdek_order_id_cdek_orders'), 'orders', type_='foreignkey')
    op.drop_constraint(op.f('uq_orders_cdek_order_id'), 'orders', type_='unique')
    op.drop_index(op.f('ix_orders_cdek_order_id'), table_name='orders')
    op.drop_column('orders', 'cdek_order_id')

    op.drop_table('cdek_status_history')
    op.drop_table('cdek_orders')
    op.drop_table('jobs')
