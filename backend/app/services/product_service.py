from sqlalchemy.orm import Session

from app.repos.product_repo import (
    create_product,
    get_product,
    search_products,
)


def create_product_service(
    db: Session,
    *,
    name: str,
    brand_id: int | None,
    category_id: int | None,
    description: str | None,
    unit: str | None,
    image_url: str | None,
):
    product = create_product(
        db,
        name=name,
        brand_id=brand_id,
        category_id=category_id,
        description=description,
        unit=unit,
        image_url=image_url,
    )

    db.commit()
    db.refresh(product)

    return product


def get_product_service(
    db: Session,
    product_id: int,
):
    return get_product(db, product_id)


def search_product_service(
    db: Session,
    query: str | None,
    category_id: int | None,
    brand_id: int | None,
    limit: int,
    offset: int,
):
    return search_products(
        db,
        query=query,
        category_id=category_id,
        brand_id=brand_id,
        limit=limit,
        offset=offset,
    )