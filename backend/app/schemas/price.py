from decimal import Decimal

from pydantic import AnyHttpUrl, BaseModel


class PriceLookupRequest(BaseModel):
    url: AnyHttpUrl


class PriceLookupResponse(BaseModel):
    source_url: AnyHttpUrl
    product_name: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    availability: str | None = None
    image_url: AnyHttpUrl | None = None
    fetched_at: str
    source_type: str



    