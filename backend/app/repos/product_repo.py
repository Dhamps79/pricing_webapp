from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.product import Product


def get_product_by_name(
    db: Session,
    name: str,
) -> Product | None:
    statement = select(Product).where(Product.name == name)
    return db.scalar(statement)


def create_product(
    db: Session,
    name: str,
    image_url: str | None,
) -> Product:
    product = Product(
        name=name,
        image_url=image_url,
    )

    db.add(product)
    db.flush()

    return product
def get_product_by_id(
    db: Session,
    product_id: int,
) -> Product | None:
    return db.get(Product, product_id)