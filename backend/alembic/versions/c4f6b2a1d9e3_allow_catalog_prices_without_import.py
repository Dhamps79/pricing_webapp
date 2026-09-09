"""allow catalog prices without an import record

Revision ID: c4f6b2a1d9e3
Revises: f8fb13581843
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c4f6b2a1d9e3"
down_revision: Union[str, Sequence[str], None] = "fix_catalog_import_created_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("catalog_prices", "import_id", nullable=True)


def downgrade() -> None:
    op.alter_column("catalog_prices", "import_id", nullable=False)