from sqlalchemy import text

from app.database.base import Base
from app.database.engine import engine
from app.database.models import (  # noqa: F401
    CostingSheet,
    CostingSheetLine,
    PriceHistory,
    Product,
    Source,
)

ALTER_STATEMENTS = [
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS sku VARCHAR(80)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS category VARCHAR(255)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS unit VARCHAR(50)",
    "ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_products_sku ON products (sku)",
    "CREATE INDEX IF NOT EXISTS ix_products_category ON products (category)",
]


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        for statement in ALTER_STATEMENTS:
            connection.execute(text(statement))
