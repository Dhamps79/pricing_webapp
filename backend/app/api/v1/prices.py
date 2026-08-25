from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.services.price_service import (
    get_current_price,
    get_product_price_history,
    track_price,
)

router = APIRouter(
    prefix="/prices",
    tags=["Prices"],
)


@router.post("/track")
async def track_product_price(
    url: str,
    db: Session = Depends(get_db),
):
    result = await track_price(
        db=db,
        url=url,
    )

    return {
        "product": {
            "id": result["product"].id,
            "name": result["product"].name,
            "image_url": result["product"].image_url,
        },
        "source": {
            "id": result["source"].id,
            "url": result["source"].url,
            "domain": result["source"].domain,
            "source_type": result["source"].source_type,
        },
        "price": {
            "id": result["price_history"].id,
            "value": str(result["price_history"].price),
            "currency": result["price_history"].currency,
            "availability": result["price_history"].availability,
            "fetched_at": result["price_history"].fetched_at,
        },
    }


@router.get("/{product_id}/history")
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

    product = result["product"]
    history = result["history"]

    return {
        "product": {
            "id": product.id,
            "name": product.name,
        },
        "history": [
            {
                "id": item.id,
                "price": str(item.price),
                "currency": item.currency,
                "availability": item.availability,
                "fetched_at": item.fetched_at,
            }
            for item in history
        ],
    }

@router.get("/{product_id}")
def get_current_product_price(
    product_id: int,
    db: Session = Depends(get_db),
):
    result = get_current_price(
        db=db,
        product_id=product_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product or price not found",
        )

    product = result["product"]
    price = result["price"]

    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "image_url": product.image_url,
        },
        "price": {
            "id": price.id,
            "value": str(price.price),
            "currency": price.currency,
            "availability": price.availability,
            "fetched_at": price.fetched_at,
        },
    }

@router.post("/{product_id}/refresh")
async def refresh_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    result = get_current_price(
        db=db,
        product_id=product_id,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Product or price not found",
        )

    product = result["product"]

    if not product.sources:
        raise HTTPException(
            status_code=404,
            detail="No source found for this product",
        )

    source = product.sources[0]

    tracked = await track_price(
        db=db,
        url=source.url,
    )

    return {
        "product": {
            "id": tracked["product"].id,
            "name": tracked["product"].name,
            "image_url": tracked["product"].image_url,
        },
        "source": {
            "id": tracked["source"].id,
            "url": tracked["source"].url,
            "domain": tracked["source"].domain,
            "source_type": tracked["source"].source_type,
        },
        "price": {
            "id": tracked["price_history"].id,
            "value": str(
                tracked["price_history"].price
            ),
            "currency": tracked["price_history"].currency,
            "availability": tracked["price_history"].availability,
            "fetched_at": tracked["price_history"].fetched_at,
        },
    }
