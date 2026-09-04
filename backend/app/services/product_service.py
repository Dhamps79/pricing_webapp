from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.models.product import Product
from app.repos.price_history_repo import get_latest_prices_for_products
from app.repos.product_repo import (
    create_product,
    delete_product,
    get_product_by_id,
    get_product_by_name,
    search_products,
    update_product,
)


def create_product_service(
    db: Session,
    *,
    name: str,
    image_url: str | None = None,
    brand_id: int | None = None,
    category_id: int | None = None,
    description: str | None = None,
    unit: str | None = None,
    is_active: bool = True,
) -> Product:
    existing = get_product_by_name(
        db=db,
        name=name.strip(),
    )

    if existing:
        raise ValueError(
            "A product with this name already exists."
        )

    product = create_product(
        db=db,
        name=name.strip(),
        image_url=image_url,
        brand_id=brand_id,
        category_id=category_id,
        description=description,
        unit=unit,
        is_active=is_active,
    )

    db.commit()
    db.refresh(product)

    return product


def update_product_service(
    db: Session,
    product_id: int,
    *,
    name: str | None = None,
    image_url: str | None = None,
    brand_id: int | None = None,
    category_id: int | None = None,
    description: str | None = None,
    unit: str | None = None,
    is_active: bool | None = None,
) -> Product:

    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise ValueError("Product not found.")

    if name is not None:
        name = name.strip()

        if not name:
            raise ValueError("Product name cannot be empty.")

        if name != product.name:
            existing = get_product_by_name(
                db=db,
                name=name,
            )

            if existing and existing.id != product.id:
                raise ValueError(
                    "A product with this name already exists."
                )

    product = update_product(
        db=db,
        product=product,
        name=name,
        image_url=image_url,
        brand_id=brand_id,
        category_id=category_id,
        description=description,
        unit=unit,
        is_active=is_active,
    )

    db.commit()
    db.refresh(product)

    return product


def delete_product_service(
    db: Session,
    product_id: int,
) -> None:

    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise ValueError("Product not found.")

    delete_product(
        db=db,
        product=product,
    )


def get_products_with_pricing(
    db: Session,
    *,
    query: str | None = None,
    category_id: int | None = None,
    brand_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
):
    products = search_products(
        db=db,
        query=query,
        category_id=category_id,
        brand_id=brand_id,
        limit=limit,
        offset=offset,
    )

    if not products:
        return []

    product_ids = [product.id for product in products]

    pricing = get_latest_prices_for_products(
        db=db,
        product_ids=product_ids,
    )

    response = []

    for product in products:
        records = pricing.get(product.id, [])

        latest = records[0] if len(records) >= 1 else None
        previous = records[1] if len(records) >= 2 else None

        latest_history = latest[0] if latest else None
        latest_source = latest[1] if latest else None

        previous_history = previous[0] if previous else None

        current_price = (
            latest_history.price
            if latest_history
            else None
        )

        previous_price = (
            previous_history.price
            if previous_history
            else None
        )

        price_change = None
        price_change_percent = None
        trend = "stable"

        if (
            current_price is not None
            and previous_price is not None
        ):
            price_change = (
                current_price - previous_price
            )

            if previous_price != 0:
                price_change_percent = (
                    price_change
                    / previous_price
                    * Decimal("100")
                )

            if current_price > previous_price:
                trend = "up"
            elif current_price < previous_price:
                trend = "down"

        response.append(
            {
                "id": product.id,
                "name": product.name,
                "brand_id": product.brand_id,
                "category_id": product.category_id,
                "description": product.description,
                "unit": product.unit,
                "image_url": product.image_url,
                "is_active": product.is_active,
                "current_price": current_price,
                "previous_price": previous_price,
                "price_change": price_change,
                "price_change_percent": price_change_percent,
                "currency": (
                    latest_history.currency
                    if latest_history
                    else None
                ),
                "availability": (
                    latest_history.availability
                    if latest_history
                    else None
                ),
                "source_url": (
                    latest_source.url
                    if latest_source
                    else None
                ),
                "source_domain": (
                    latest_source.domain
                    if latest_source
                    else None
                ),
                "fetched_at": (
                    latest_history.fetched_at
                    if latest_history
                    else None
                ),
                "trend": trend,
            }
        )

    return response