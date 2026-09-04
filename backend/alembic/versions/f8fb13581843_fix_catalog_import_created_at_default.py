from alembic import op


revision = "fix_catalog_import_created_at"
down_revision = "0001_initial_schema","cb2aac7a347e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE catalog_imports
        ALTER COLUMN created_at
        SET DEFAULT NOW()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE catalog_imports
        ALTER COLUMN created_at
        DROP DEFAULT
        """
    )