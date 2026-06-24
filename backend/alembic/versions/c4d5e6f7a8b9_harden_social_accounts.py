"""harden social_accounts: drop access_token, composite unique

Security review (issue #4):
- F-04: drop plaintext ``access_token`` column (it was never read).
- F-12: replace global unique on ``provider_id`` with a composite
  unique ``(provider, provider_id)``.

Revision ID: c4d5e6f7a8b9
Revises: 2ad164310a94
Create Date: 2026-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "2ad164310a94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # F-12: drop old single-column unique, add composite unique + index.
    op.drop_constraint(
        "social_accounts_provider_id_key", "social_accounts", type_="unique"
    )
    op.create_index(
        op.f("ix_social_accounts_provider_id"),
        "social_accounts",
        ["provider_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_social_provider_provider_id",
        "social_accounts",
        ["provider", "provider_id"],
    )
    # F-04: drop plaintext provider access token.
    op.drop_column("social_accounts", "access_token")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "social_accounts",
        sa.Column("access_token", sa.String(), nullable=True),
    )
    op.drop_constraint(
        "uq_social_provider_provider_id", "social_accounts", type_="unique"
    )
    op.drop_index(
        op.f("ix_social_accounts_provider_id"), table_name="social_accounts"
    )
    op.create_unique_constraint(
        "social_accounts_provider_id_key", "social_accounts", ["provider_id"]
    )
