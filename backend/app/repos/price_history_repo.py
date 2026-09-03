from datetime import datetime
from decimal import Decimal

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
    product_ids: list[int],
) -> dict[int, list[tuple[PriceHistory, Source]]]:
    """
    Return the two most recent price records for every product,
    together with their Source.

    Uses one SQL query for all requested products.
    """

    if not product_ids:
        return {}

    ranked = (
        select(
            PriceHistory.id.label("id"),
            func.row_number()
            .over(
                partition_by=PriceHistory.product_id,
                order_by=(
                    PriceHistory.fetched_at.desc(),
                    PriceHistory.id.desc(),
                ),
            )
            .label("price_rank"),
        )
        .where(
            PriceHistory.product_id.in_(product_ids)
        )
        .subquery()
    )

    statement = (
        select(
            PriceHistory,
            Source,
        )
        .join(
            ranked,
            PriceHistory.id == ranked.c.id,
        )
        .join(
            Source,
            PriceHistory.source_id == Source.id,
        )
        .where(
            ranked.c.price_rank <= 2
        )
        .order_by(
            PriceHistory.product_id.asc(),
            PriceHistory.fetched_at.desc(),
            PriceHistory.id.desc(),
        )
    )

    records = db.execute(statement).all()

    result: dict[int, list[tuple[PriceHistory, Source]]] = {}

    for price_history, source in records:
        result.setdefault(
            price_history.product_id,
            [],
        ).append(
            (price_history, source)
        )

    return result