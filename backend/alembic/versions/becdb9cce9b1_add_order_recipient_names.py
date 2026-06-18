"""Add recipient first/last name columns to orders.

Revision ID: becdb9cce9b1
Revises: 6ed3c871235e
Create Date: 2026-06-18 04:38:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "becdb9cce9b1"
down_revision: Union[str, Sequence[str], None] = "6ed3c871235e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("recipient_first_name", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("recipient_last_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "recipient_last_name")
    op.drop_column("orders", "recipient_first_name")
