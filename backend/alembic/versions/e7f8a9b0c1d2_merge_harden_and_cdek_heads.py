"""merge harden_social_accounts and cdek_orders heads

Two alembic heads diverged from 2ad164310a94:
  - c4d5e6f7a8b9 (harden social_accounts — OAuth/JWT hardening, PR #8)
  - fbdcfbb48f7d (merge of user_addresses + cdek_orders_and_jobs)
`alembic upgrade head` is ambiguous with multiple heads, which breaks the
deploy migrate job. This is a no-op merge revision that unifies them into a
single head; no schema change.

Revision ID: e7f8a9b0c1d2
Revises: c4d5e6f7a8b9, fbdcfbb48f7d
Create Date: 2026-06-24 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = ('c4d5e6f7a8b9', 'fbdcfbb48f7d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
