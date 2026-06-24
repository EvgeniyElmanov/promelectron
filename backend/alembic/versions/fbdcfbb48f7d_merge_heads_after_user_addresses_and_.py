"""merge heads after user_addresses and cdek_jobs

Revision ID: fbdcfbb48f7d
Revises: 2ad164310a94, 9a1b2c3d4e5f
Create Date: 2026-06-24 14:30:53.357204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbdcfbb48f7d'
down_revision: Union[str, Sequence[str], None] = ('2ad164310a94', '9a1b2c3d4e5f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
