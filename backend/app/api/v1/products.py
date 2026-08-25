from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.database.models.product import Product

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.get("")
def get_products(
    db: Session = Depends(get_db),
):
    products = (
        db.query(Product)
        .order_by(Product.id.desc())
        .all()
    )

    return products


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted successfully",
        "product_id": product_id,
    }