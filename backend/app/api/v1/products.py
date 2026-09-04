from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.repos.product_repo import get_product_by_id
from app.schemas.pricehistory import PriceHistoryResponse
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import (
    create_product_service,
    delete_product_service,
    get_products_with_pricing,
    update_product_service,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_endpoint(
    payload: ProductCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_product_service(
            db=db,
            name=payload.name,
            brand_id=payload.brand_id,
            category_id=payload.category_id,
            description=payload.description,
            unit=payload.unit,
            image_url=payload.image_url,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product conflicts with an existing record.",
        ) from exc


@router.get(
    "",
    response_model=list[ProductResponse],
)
def search_products_endpoint(
    q: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),
    category_id: int | None = Query(default=None),
    brand_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return get_products_with_pricing(
        db=db,
        query=q,
        category_id=category_id,
        brand_id=brand_id,
        limit=limit,
        offset=offset,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return product


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product_endpoint(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_product_service(
            db=db,
            product_id=product_id,
            name=payload.name,
            image_url=payload.image_url,
            brand_id=payload.brand_id,
            category_id=payload.category_id,
            description=payload.description,
            unit=payload.unit,
            is_active=payload.is_active,
        )

    except ValueError as exc:
        message = str(exc)

        if "not found" in message.lower():
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=code,
            detail=message,
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to update product because of a database conflict.",
        ) from exc

@router.get(
    "/{product_id}/history",
    response_model=PriceHistoryResponse,
)
def get_product_history(
    product_id: int,
    db: Session = Depends(get_db),
):
    result = get_product_price_history(
        db=db,
        product_id=product_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return {
        "product": {
            "id": result["product"].id,
            "name": result["product"].name,
        },
        "history": [
            {
                "id": item.id,
                "price": item.price,
                "currency": item.currency,
                "availability": item.availability,
                "fetched_at": item.fetched_at,
            }
            for item in result["history"]
        ],
    }

@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_product_service(
            db=db,
            product_id=product_id,
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to delete product because dependent records exist.",
        ) from exc

    return None