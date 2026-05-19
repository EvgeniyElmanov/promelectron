"""merge tracking_number and delivery_methods

Revision ID: 58c166b0f3ce
Revises: 9ad1175f551e, 4a2e8c9d1f00
Create Date: 2026-05-20 10:42:15.788512

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58c166b0f3ce'
down_revision: Union[str, Sequence[str], None] = ('9ad1175f551e', '4a2e8c9d1f00')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
