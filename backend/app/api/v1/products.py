from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.schemas.product import ProductCreate, ProductResponse
from app.services.product_service import (
    create_product_service,
    delete_product_service,
    update_product_service,
)
from app.repos.product_repo import (
    get_product_by_id,
    search_products,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductResponse,
)
def create_product_endpoint(
    payload: ProductCreate,
    db: Session = Depends(get_db),
):

    return create_product_service(
        db,
        name=payload.name,
        brand_id=payload.brand_id,
        category_id=payload.category_id,
        description=payload.description,
        unit=payload.unit,
        image_url=payload.image_url,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
):

    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@router.get(
    "",
    response_model=list[ProductResponse],
)
def search_products_endpoint(
    q: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    brand_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):

    return search_products(
        db=db,
        query=q,
        category_id=category_id,
        brand_id=brand_id,
        limit=limit,
        offset=offset,
    )