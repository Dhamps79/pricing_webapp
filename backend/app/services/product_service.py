from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.product import Product
from app.database.models.source import Source
from app.database.models.price_history import PriceHistory


def list_products(db: Session):
    # ---------------------------------------------------------
    # QUERY 1
    # Get all products
    # ---------------------------------------------------------
    products = db.scalars(
        select(Product)
        .where(Product.sku.is_(None))
        .order_by(Product.id.desc())
    ).all()

    if not products:
        return []

    product_ids = [product.id for product in products]

    # ---------------------------------------------------------
    # QUERY 2
    # Get the latest Source for each product
    # ---------------------------------------------------------
    source_rank = (
        select(
            Source.id,
            Source.product_id,
            Source.url,
            Source.domain,
            Source.source_type,
            func.row_number()
            .over(
                partition_by=Source.product_id,
                order_by=Source.id.desc(),
            )
            .label("row_number"),
        )
        .where(Source.product_id.in_(product_ids))
        .subquery()
    )

    latest_sources = db.execute(
        select(
            source_rank.c.product_id,
            source_rank.c.url,
            source_rank.c.domain,
            source_rank.c.source_type,
        ).where(source_rank.c.row_number == 1)
    ).all()

    sources_by_product = {
        row.product_id: row
        for row in latest_sources
    }

    # ---------------------------------------------------------
    # QUERY 3
    # Get latest TWO price records for each product
    # ---------------------------------------------------------
    price_rank = (
        select(
            PriceHistory.id,
            PriceHistory.product_id,
            PriceHistory.source_id,
            PriceHistory.price,
            PriceHistory.currency,
            PriceHistory.availability,
            PriceHistory.fetched_at,
            func.row_number()
            .over(
                partition_by=PriceHistory.product_id,
                order_by=PriceHistory.fetched_at.desc(),
            )
            .label("row_number"),
        )
        .where(
            PriceHistory.product_id.in_(product_ids)
        )
        .subquery()
    )

    price_rows = db.execute(
        select(
            price_rank.c.id,
            price_rank.c.product_id,
            price_rank.c.source_id,
            price_rank.c.price,
            price_rank.c.currency,
            price_rank.c.availability,
            price_rank.c.fetched_at,
            price_rank.c.row_number,
        ).where(price_rank.c.row_number <= 2)
    ).all()

    prices_by_product: dict[int, list] = {}

    for row in price_rows:
        prices_by_product.setdefault(
            row.product_id,
            [],
        ).append(row)

    # ---------------------------------------------------------
    # Build API response
    # ---------------------------------------------------------
    result = []

    for product in products:
        source = sources_by_product.get(product.id)

        price_records = prices_by_product.get(
            product.id,
            [],
        )

        # Because row_number 1 is latest
        latest = next(
            (
                row
                for row in price_records
                if row.row_number == 1
            ),
            None,
        )

        previous = next(
            (
                row
                for row in price_records
                if row.row_number == 2
            ),
            None,
        )

        # -----------------------------------------------------
        # Calculate trend
        # -----------------------------------------------------
        trend = "stable"

        if latest and previous:
            if latest.price > previous.price:
                trend = "up"

            elif latest.price < previous.price:
                trend = "down"

        result.append(
            {
                "id": product.id,
                "name": product.name,
                "image_url": product.image_url,

                "current_price": (
                    latest.price
                    if latest
                    else None
                ),

                "currency": (
                    latest.currency
                    if latest
                    else None
                ),

                "availability": (
                    latest.availability
                    if latest
                    else None
                ),

                "source_url": (
                    source.url
                    if source
                    else None
                ),

                "source_domain": (
                    source.domain
                    if source
                    else None
                ),

                "fetched_at": (
                    latest.fetched_at
                    if latest
                    else None
                ),

                "trend": trend,
            }
        )

    return result