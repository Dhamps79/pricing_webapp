from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
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
    upload_catalog_pdf,
)


router = APIRouter(
    prefix="/catalog",
    tags=["Catalog"],
)


@router.post("/imports/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    supplier_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Upload and extract a catalog PDF.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty.",
        )

    try:
        import_record = upload_catalog_pdf(
            db,
            contents=contents,
            original_filename=file.filename,
            supplier_name=supplier_name,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Catalog PDF import failed: {exc}",
        ) from exc

    return {
        "id": import_record.id,
        "file_name": import_record.file_name,
        "supplier_name": import_record.supplier_name,
        "status": import_record.status,
        "total_rows": import_record.total_rows,
        "imported_rows": import_record.imported_rows,
        "failed_rows": import_record.failed_rows,
        "created_at": import_record.created_at,
    }


@router.get("/items")
def search_catalog_items(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(
        default=40,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: Session = Depends(get_db),
):
    """
    Search catalog products and attach their latest price.
    """

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
        "total": count_catalog(
            db,
            query=q,
            category=category,
        ),
        "items": items,
    }


@router.get("/categories")
def get_catalog_categories(
    db: Session = Depends(get_db),
):
    return {
        "categories": list_categories(db),
    }