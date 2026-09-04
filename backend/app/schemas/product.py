from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductAttributeCreate(BaseModel):
    attribute_name: str = Field(min_length=1, max_length=200)
    attribute_value: str = Field(min_length=1, max_length=1000)


class ProductCodeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=200)
    code_type: str = Field(min_length=1, max_length=50)
    is_primary: bool = False


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)

    brand_id: int | None = None
    category_id: int | None = None

    description: str | None = None
    unit: str | None = Field(default=None, max_length=50)
    image_url: str | None = None

    codes: list[ProductCodeCreate] = Field(default_factory=list)
    attributes: list[ProductAttributeCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    brand_id: int | None = None
    category_id: int | None = None
    description: str | None = None
    unit: str | None = Field(default=None, max_length=50)
    image_url: str | None = None
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand_id: int | None
    category_id: int | None
    description: str | None
    unit: str | None
    image_url: str | None
    is_active: bool

    current_price: Decimal | None = None
    previous_price: Decimal | None = None
    price_change: Decimal | None = None
    price_change_percent: Decimal | None = None

    currency: str | None = None
    availability: str | None = None

    source_url: str | None = None
    source_domain: str | None = None
    fetched_at: datetime | None = None

    trend: str | None = None