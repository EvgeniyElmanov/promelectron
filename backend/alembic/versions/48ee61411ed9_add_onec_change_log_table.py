"""add onec_change_log table

Revision ID: 48ee61411ed9
Revises: 9614c59dd5a3
Create Date: 2026-07-11 06:30:15.100087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '48ee61411ed9'
down_revision: Union[str, Sequence[str], None] = '9614c59dd5a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'onec_change_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('payload_size_bytes', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_onec_change_log_batch_id'), 'onec_change_log', ['batch_id'], unique=False)
    op.create_index(op.f('ix_onec_change_log_checksum'), 'onec_change_log', ['checksum'], unique=False)
    op.create_index(op.f('ix_onec_change_log_entity_type'), 'onec_change_log', ['entity_type'], unique=False)
    op.create_index(op.f('ix_onec_change_log_status'), 'onec_change_log', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_onec_change_log_status'), table_name='onec_change_log')
    op.drop_index(op.f('ix_onec_change_log_entity_type'), table_name='onec_change_log')
    op.drop_index(op.f('ix_onec_change_log_checksum'), table_name='onec_change_log')
    op.drop_index(op.f('ix_onec_change_log_batch_id'), table_name='onec_change_log')
    op.drop_table('onec_change_log')
