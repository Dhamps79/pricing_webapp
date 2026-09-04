from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PriceHistoryItem(BaseModel):
    id: int
    price: Decimal
    currency: str | None
    availability: str | None
    fetched_at: datetime


class PriceHistoryProduct(BaseModel):
    id: int
    name: str


class PriceHistoryResponse(BaseModel):
    product: PriceHistoryProduct
    history: list[PriceHistoryItem]