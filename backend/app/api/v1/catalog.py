from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.repos.catalog_repo import (
    count_catalog,
    latest_prices_for_products,
    list_categories,
    search_catalog,
)
from app.services.catalog_import_service import (
    catalog_item_payload,
    import_pricelists,
)

router = APIRouter(
    prefix="/catalog",
    tags=["Catalog"],
)


@router.get("/items")
def search_catalog_items(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=40, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    products = search_catalog(
        db,
        query=q,
        category=category,
        limit=limit,
        offset=offset,
    )
    prices = latest_prices_for_products(
        db,
        [product.id for product in products],
    )
    items = []
    for product in products:
        latest = prices.get(product.id)
        items.append(
            catalog_item_payload(
                product,
                latest.price if latest else None,
                latest.currency if latest else "INR",
            )
        )

    return {
        "total": count_catalog(db, query=q, category=category),
        "items": items,
    }


@router.get("/categories")
def get_catalog_categories(
    db: Session = Depends(get_db),
):
    return {"categories": list_categories(db)}


@router.post("/import")
def import_catalog(
    db: Session = Depends(get_db),
):
    try:
        result = import_pricelists(db)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return result
