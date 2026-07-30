"""add_onec_intake_log

Revision ID: 937fc6751168
Revises: 8965b510122d
Create Date: 2026-07-30 08:22:19.775022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '937fc6751168'
down_revision: Union[str, Sequence[str], None] = '8965b510122d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('onec_intake_log',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('intake_id', sa.UUID(), nullable=False),
    sa.Column('bucket', sa.String(length=128), nullable=False),
    sa.Column('object_key', sa.String(length=512), nullable=False),
    sa.Column('content_type', sa.String(length=255), nullable=True),
    sa.Column('received_bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('query_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('remote_addr', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=512), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onec_intake_log_intake_id'), 'onec_intake_log', ['intake_id'], unique=True)
    op.create_index(op.f('ix_onec_intake_log_sha256'), 'onec_intake_log', ['sha256'], unique=False)
    op.create_index(op.f('ix_onec_intake_log_status'), 'onec_intake_log', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_onec_intake_log_status'), table_name='onec_intake_log')
    op.drop_index(op.f('ix_onec_intake_log_sha256'), table_name='onec_intake_log')
    op.drop_index(op.f('ix_onec_intake_log_intake_id'), table_name='onec_intake_log')
    op.drop_table('onec_intake_log')
