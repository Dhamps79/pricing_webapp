from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.product import Product


def get_all_products(db: Session) -> list[Product]:
    statement = select(Product).order_by(Product.id.desc())

    return list(db.scalars(statement).all())