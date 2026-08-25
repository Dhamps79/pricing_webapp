from sqlalchemy.orm import Session

from app.database.models.product import Product


def get_product(
    db: Session,
    product_id: int,
) -> Product | None:
    return (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )


def get_product_by_id(
    db: Session,
    product_id: int,
) -> Product | None:
    return get_product(
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
    search: str,
) -> list[Product]:
    query = (
        db.query(Product)
        .filter(
            Product.name.ilike(f"%{search}%")
        )
    )

    return query.order_by(Product.name.asc()).all()

def create_product(
    db: Session,
    *,
    name: str,
    sku: str,
    category_id: int | None = None,
    brand_id: int | None = None,
    unit_id: int | None = None,
) -> Product:

    product = Product(
        name=name,
        sku=sku,
        category_id=category_id,
        brand_id=brand_id,
        unit_id=unit_id,
    )

    db.add(product)
    db.flush()

    return product