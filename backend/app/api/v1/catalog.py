from pathlib import Path
from uuid import uuid4

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
    create_import_record,
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
async def upload_catalog(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    unique_name = (
        f"{uuid4().hex}{extension}"
    )

    file_path = UPLOAD_DIR / unique_name

    try:
        contents = await file.read()

        with open(file_path, "wb") as output_file:
            output_file.write(contents)

        catalog_import = create_import_record(
            db=db,
            file_name=file.filename,
            file_path=str(file_path),
            supplier_name="Siemens",
        )

        db.commit()
        db.refresh(catalog_import)

        return {
            "id": catalog_import.id,
            "file_name": catalog_import.file_name,
            "status": catalog_import.status,
            "total_rows": catalog_import.total_rows,
            "imported_rows": catalog_import.imported_rows,
            "failed_rows": catalog_import.failed_rows,
        }

    except Exception as exc:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Unable to upload catalog.",
        ) from exc

    return result
