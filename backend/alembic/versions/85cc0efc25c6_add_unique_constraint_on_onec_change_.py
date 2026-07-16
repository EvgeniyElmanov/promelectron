"""add unique constraint on onec_change_log.batch_id

Revision ID: 85cc0efc25c6
Revises: 00eea8e26e66
Create Date: 2026-07-13 17:03:21.273851

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '85cc0efc25c6'
down_revision: Union[str, Sequence[str], None] = '00eea8e26e66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make onec_change_log.batch_id unique for idempotency."""
    op.drop_index(op.f('ix_onec_change_log_batch_id'), table_name='onec_change_log')
    op.create_index(
        op.f('ix_onec_change_log_batch_id'),
        'onec_change_log',
        ['batch_id'],
        unique=True,
    )


def downgrade() -> None:
    """Restore non-unique batch_id index."""
    op.drop_index(op.f('ix_onec_change_log_batch_id'), table_name='onec_change_log')
    op.create_index(
        op.f('ix_onec_change_log_batch_id'),
        'onec_change_log',
        ['batch_id'],
        unique=False,
    )
