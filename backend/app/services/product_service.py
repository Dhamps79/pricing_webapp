from sqlalchemy.orm import Session

from app.database.models.product import Product
from app.repos.product_repo import (
    create_product,
    delete_product,
    get_product,
    get_product_by_name,
    get_product_by_sku,
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
        name=name,
    )

    if existing:
        raise ValueError(
            "A product with this name already exists."
        )

    return create_product(
        db=db,
        name=name,
        image_url=image_url,
        brand_id=brand_id,
        category_id=category_id,
        description=description,
        unit=unit,
        is_active=is_active,
    )


def get_product_service(
    db: Session,
    product_id: int,
) -> Product | None:

    return get_product(
        db=db,
        product_id=product_id,
    )


def search_product_service(
    db: Session,
    *,
    query: str | None = None,
    category_id: int | None = None,
    brand_id: int | None = None,
    is_active: bool | None = True,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:

    return search_products(
        db=db,
        query=query,
        category_id=category_id,
        brand_id=brand_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


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

    product = get_product(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise ValueError(
            "Product not found."
        )

    if name is not None and name != product.name:
        existing = get_product_by_name(
            db=db,
            name=name,
        )

        if existing and existing.id != product.id:
            raise ValueError(
                "A product with this name already exists."
            )

    return update_product(
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


def delete_product_service(
    db: Session,
    product_id: int,
) -> None:

    product = get_product(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise ValueError(
            "Product not found."
        )

    delete_product(
        db=db,
        product=product,
    )