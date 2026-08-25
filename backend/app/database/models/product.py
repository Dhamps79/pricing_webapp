from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.brand import Brand
    from app.database.models.category import Category
    from app.database.models.costing_sheet_line import CostingSheetLine
    from app.database.models.price_history import PriceHistory
    from app.database.models.product_attribute import ProductAttribute
    from app.database.models.product_code import ProductCode
    from app.database.models.source import Source


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )

    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    brand: Mapped["Brand | None"] = relationship(
        back_populates="products",
    )

    category: Mapped["Category | None"] = relationship(
        back_populates="products",
    )

    codes: Mapped[list["ProductCode"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    attributes: Mapped[list["ProductAttribute"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    sources: Mapped[list["Source"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    costing_lines: Mapped[list["CostingSheetLine"]] = relationship(
        back_populates="product",
    )