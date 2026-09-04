"""initial application schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Brands
    # ------------------------------------------------------------------

    op.create_table(
        "brands",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("code"),
    )

    op.create_index(
        "ix_brands_name",
        "brands",
        ["name"],
        unique=False,
    )

    op.create_index(
        "ix_brands_code",
        "brands",
        ["code"],
        unique=False,
    )

    op.create_index(
        "ix_brands_is_active",
        "brands",
        ["is_active"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    op.create_table(
        "categories",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_index(
        "ix_categories_name",
        "categories",
        ["name"],
        unique=False,
    )

    op.create_index(
        "ix_categories_is_active",
        "categories",
        ["is_active"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    op.create_table(
        "products",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            "brand_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "unit",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "image_url",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brands.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_products_name",
        "products",
        ["name"],
        unique=False,
    )

    op.create_index(
        "ix_products_brand_id",
        "products",
        ["brand_id"],
        unique=False,
    )

    op.create_index(
        "ix_products_category_id",
        "products",
        ["category_id"],
        unique=False,
    )

    op.create_index(
        "ix_products_unit",
        "products",
        ["unit"],
        unique=False,
    )

    op.create_index(
        "ix_products_is_active",
        "products",
        ["is_active"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Product codes
    # ------------------------------------------------------------------

    op.create_table(
        "product_codes",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "code_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_index(
        "ix_product_codes_product_id",
        "product_codes",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        "ix_product_codes_code",
        "product_codes",
        ["code"],
        unique=False,
    )

    op.create_index(
        "ix_product_codes_code_type",
        "product_codes",
        ["code_type"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Product attributes
    # ------------------------------------------------------------------

    op.create_table(
        "product_attributes",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "attribute_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "attribute_value",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "attribute_name",
            name="uq_product_attribute",
        ),
    )

    op.create_index(
        "ix_product_attributes_product_id",
        "product_attributes",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        "ix_product_attributes_attribute_name",
        "product_attributes",
        ["attribute_name"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Catalog imports
    # ------------------------------------------------------------------

    op.create_table(
        "catalog_imports",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "file_path",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "supplier_name",
            sa.String(length=150),
            nullable=True,
        ),
        sa.Column(
            "effective_date",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column(
            "total_rows",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "imported_rows",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "failed_rows",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_catalog_imports_id",
        "catalog_imports",
        ["id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Catalog import rows
    # ------------------------------------------------------------------

    op.create_table(
        "catalog_import_rows",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "import_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "page_number",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "row_number",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "raw_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "parsed_status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["import_id"],
            ["catalog_imports.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_catalog_import_rows_import_id",
        "catalog_import_rows",
        ["import_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Catalog prices
    # ------------------------------------------------------------------

    op.create_table(
        "catalog_prices",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "import_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "price",
            sa.Numeric(12, 2),
            nullable=True,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default="INR",
        ),
        sa.Column(
            "unit",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "standard_package",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["import_id"],
            ["catalog_imports.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_catalog_prices_product_id",
        "catalog_prices",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        "ix_catalog_prices_import_id",
        "catalog_prices",
        ["import_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    op.create_table(
        "sources",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "url",
            sa.String(length=2000),
            nullable=False,
        ),
        sa.Column(
            "domain",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_sources_product_id",
        "sources",
        ["product_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Price history
    # ------------------------------------------------------------------

    op.create_table(
        "price_history",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "price",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "availability",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_price_history_product_id",
        "price_history",
        ["product_id"],
        unique=False,
    )

    op.create_index(
        "ix_price_history_source_id",
        "price_history",
        ["source_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Costing sheets
    # ------------------------------------------------------------------

    op.create_table(
        "costing_sheets",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "customer_name",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "discount_percent",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------
    # Costing sheet lines
    # ------------------------------------------------------------------

    op.create_table(
        "costing_sheet_lines",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "costing_sheet_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "list_price",
            sa.Numeric(14, 2),
            nullable=False,
        ),
        sa.Column(
            "sell_price",
            sa.Numeric(14, 2),
            nullable=False,
        ),
        sa.Column(
            "discount_percent",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "unit",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["costing_sheet_id"],
            ["costing_sheets.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_costing_sheet_lines_costing_sheet_id",
        "costing_sheet_lines",
        ["costing_sheet_id"],
        unique=False,
    )

    op.create_index(
        "ix_costing_sheet_lines_product_id",
        "costing_sheet_lines",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_costing_sheet_lines_product_id",
        table_name="costing_sheet_lines",
    )

    op.drop_index(
        "ix_costing_sheet_lines_costing_sheet_id",
        table_name="costing_sheet_lines",
    )

    op.drop_table("costing_sheet_lines")
    op.drop_table("costing_sheets")

    op.drop_index(
        "ix_price_history_source_id",
        table_name="price_history",
    )

    op.drop_index(
        "ix_price_history_product_id",
        table_name="price_history",
    )

    op.drop_table("price_history")

    op.drop_index(
        "ix_sources_product_id",
        table_name="sources",
    )

    op.drop_table("sources")

    op.drop_index(
        "ix_catalog_prices_import_id",
        table_name="catalog_prices",
    )

    op.drop_index(
        "ix_catalog_prices_product_id",
        table_name="catalog_prices",
    )

    op.drop_table("catalog_prices")

    op.drop_index(
        "ix_catalog_import_rows_import_id",
        table_name="catalog_import_rows",
    )

    op.drop_table("catalog_import_rows")

    op.drop_index(
        "ix_catalog_imports_id",
        table_name="catalog_imports",
    )

    op.drop_table("catalog_imports")

    op.drop_index(
        "ix_product_attributes_attribute_name",
        table_name="product_attributes",
    )

    op.drop_index(
        "ix_product_attributes_product_id",
        table_name="product_attributes",
    )

    op.drop_table("product_attributes")

    op.drop_index(
        "ix_product_codes_code_type",
        table_name="product_codes",
    )

    op.drop_index(
        "ix_product_codes_code",
        table_name="product_codes",
    )

    op.drop_index(
        "ix_product_codes_product_id",
        table_name="product_codes",
    )

    op.drop_table("product_codes")

    op.drop_index(
        "ix_products_is_active",
        table_name="products",
    )

    op.drop_index(
        "ix_products_unit",
        table_name="products",
    )

    op.drop_index(
        "ix_products_category_id",
        table_name="products",
    )

    op.drop_index(
        "ix_products_brand_id",
        table_name="products",
    )

    op.drop_index(
        "ix_products_name",
        table_name="products",
    )

    op.drop_table("products")

    op.drop_index(
        "ix_categories_is_active",
        table_name="categories",
    )

    op.drop_index(
        "ix_categories_name",
        table_name="categories",
    )

    op.drop_table("categories")

    op.drop_index(
        "ix_brands_is_active",
        table_name="brands",
    )

    op.drop_index(
        "ix_brands_code",
        table_name="brands",
    )

    op.drop_index(
        "ix_brands_name",
        table_name="brands",
    )

    op.drop_table("brands")