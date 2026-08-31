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
from app.services.pdf_service import extract_pdf_to_raw_rows
from sqlalchemy.orm import Session   
from app.database.sessions import get_db
from app.services.catalog_import_service import (
    catalog_item_payload,
    import_pricelists,
    create_import_record,
    extract_and_store_pdf_rows,
    upload_catalog_pdf,
    get_import,
    
)
UPLOAD_DIR = Path("storage/catalogs")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


router = APIRouter(
    prefix="/catalog",
    tags=["Catalog"],
)

@router.post("/imports/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    supplier_name: str | None = Query(
        default=None,
    ),
    db: Session = Depends(get_db),
):
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
def upload_catalog_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    unique_name = (
        f"{uuid4().hex}_"
        f"{file.filename}"
    )

    file_path = UPLOAD_DIR / unique_name

    with file_path.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            output.write(chunk)

    import_record = create_import_record(
        db=db,
        file_name=file.filename,
        file_path=str(file_path),
    )

    try:

        total_rows = extract_and_store_pdf_rows(
            db=db,
            import_id=import_record.id,
            file_path=str(file_path),
        )

        import_record.total_rows = total_rows
        import_record.status = "extracted"

        db.commit()
        db.refresh(import_record)

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"PDF extraction failed: {exc}",
        )

    return {
        "import_id": import_record.id,
        "file_name": import_record.file_name,
        "status": import_record.status,
        "total_rows": total_rows,
    }
