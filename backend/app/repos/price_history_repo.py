from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.price_history import PriceHistory
from app.database.models.source import Source


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
        .order_by(
            PriceHistory.fetched_at.desc(),
            PriceHistory.id.desc(),
        )
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
        .order_by(
            PriceHistory.fetched_at.desc(),
            PriceHistory.id.desc(),
        )
    )

    return list(db.scalars(statement).all())


def get_latest_prices_for_products(
    db: Session,
    *,
    product_ids: list[int],
):
    if not product_ids:
        return {}

    ranked = (
        db.query(
            PriceHistory.id.label("price_id"),
            func.row_number()
            .over(
                partition_by=PriceHistory.product_id,
                order_by=PriceHistory.fetched_at.desc(),
            )
            .label("rn"),
        )
        .filter(
            PriceHistory.product_id.in_(product_ids)
        )
        .subquery()
    )

    rows = (
        db.query(
            PriceHistory,
            Source,
        )
        .join(
            ranked,
            ranked.c.price_id == PriceHistory.id,
        )
        .join(
            Source,
            Source.id == PriceHistory.source_id,
        )
        .filter(
            ranked.c.rn <= 2
        )
        .order_by(
            PriceHistory.product_id,
            PriceHistory.fetched_at.desc(),
        )
        .all()
    )

    result = defaultdict(list)

    for history, source in rows:
        result[history.product_id].append(
            (history, source)
        )

    return dict(result)