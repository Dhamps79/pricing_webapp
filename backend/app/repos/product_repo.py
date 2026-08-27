from sqlalchemy.orm import Session

from app.database.models.product import Product


def get_product_by_id(
    db: Session,
    product_id: int,
) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )


def get_product(
    db: Session,
    product_id: int,
) -> Product | None:
    return get_product_by_id(
        db=db,
        product_id=product_id,
    )


def get_product_by_sku(
    db: Session,
    sku: str,
) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.sku == sku)
        .first()
    )


def get_product_by_name(
    db: Session,
    name: str,
) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.name == name)
        .first()
    )


def search_products(
    db: Session,
    *,
    query: str | None = None,
    category_id: int | None = None,
    brand_id: int | None = None,
    is_active: bool | None = True,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:

    db_query = db.query(Product)

    if query:
        search_term = f"%{query.strip()}%"

        db_query = db_query.filter(
            Product.name.ilike(search_term)
        )

    if category_id is not None:
        db_query = db_query.filter(
            Product.category_id == category_id
        )

    if brand_id is not None:
        db_query = db_query.filter(
            Product.brand_id == brand_id
        )

    if is_active is not None:
        db_query = db_query.filter(
            Product.is_active == is_active
        )

    return (
        db_query
        .order_by(Product.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def create_product(
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

    product = Product(
        name=name,
        image_url=image_url,
        brand_id=brand_id,
        category_id=category_id,
        description=description,
        unit=unit,
        is_active=is_active,
    )

    db.add(product)
    db.flush()

    return product


def update_product(
    db: Session,
    product: Product,
    *,
    name: str | None = None,
    image_url: str | None = None,
    brand_id: int | None = None,
    category_id: int | None = None,
    description: str | None = None,
    unit: str | None = None,
    is_active: bool | None = None,
) -> Product:

    if name is not None:
        product.name = name

    if image_url is not None:
        product.image_url = image_url

    if brand_id is not None:
        product.brand_id = brand_id

    if category_id is not None:
        product.category_id = category_id

    if description is not None:
        product.description = description

    if unit is not None:
        product.unit = unit

    if is_active is not None:
        product.is_active = is_active

    db.flush()

    return product


def delete_product(
    db: Session,
    product: Product,
) -> None:
    db.delete(product)
    db.flush()