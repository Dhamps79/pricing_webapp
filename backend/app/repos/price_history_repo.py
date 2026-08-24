from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.price_history import PriceHistory



def create_price_history(
    db: Session,
    product_id: int,
    source_id: int,
    price: Decimal,
    currency: str,
    availability: str | None,
    fetched_at: datetime,
) -> PriceHistory:
    history = PriceHistory(
        product_id=product_id,
        source_id=source_id,
        price=price,
        currency=currency,
        availability=availability,
        fetched_at=fetched_at,
    )

    db.add(history)
    db.flush()

    return history
def get_latest_price(
    db: Session,
    product_id: int,
) -> PriceHistory | None:
    statement = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.fetched_at.desc())
        .limit(1)
    )

    return db.scalar(statement)


def get_price_history(
    db: Session,
    product_id: int,
) -> list[PriceHistory]:
    statement = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.fetched_at.desc())
    )

    return list(db.scalars(statement).all())
