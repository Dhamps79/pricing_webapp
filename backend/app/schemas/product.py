from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProductResponse(BaseModel):
    id: int

    name: str

    image_url: str | None

    current_price: Decimal | None

    currency: str | None

    availability: str | None

    source_url: str | None

    source_domain: str | None

    fetched_at: datetime | None

    trend: str