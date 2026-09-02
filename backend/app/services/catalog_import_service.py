from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database.models.catalog_import import CatalogImport
from app.repos.catalog_repo import (
    create_catalog_import,
    create_catalog_import_row,
    get_catalog_import,
)
from app.services.pdf_service import extract_pdf_to_raw_rows


CATALOG_STORAGE_DIR = Path("storage/catalog")


def save_catalog_pdf(
    *,
    contents: bytes,
    original_filename: str,
) -> tuple[str, str]:
    """
    Save an uploaded catalog PDF to local storage.

    Returns:
        (stored_filename, stored_path)
    """

    if not original_filename:
        raise ValueError("Filename is required.")

    if Path(original_filename).suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    CATALOG_STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = f"{uuid4().hex}.pdf"
    stored_path = CATALOG_STORAGE_DIR / stored_filename

    stored_path.write_bytes(contents)

    return stored_filename, str(stored_path)


def extract_and_store_pdf_rows(
    db: Session,
    *,
    import_id: int,
    file_path: str,
) -> int:
    """
    Extract raw rows from a PDF and persist them
    as CatalogImportRow records.
    """

    raw_rows = extract_pdf_to_raw_rows(file_path)

    for item in raw_rows:
        create_catalog_import_row(
            db,
            import_id=import_id,
            page_number=item["page_number"],
            row_number=item["row_number"],
            raw_text=item["raw_text"],
        )

    return len(raw_rows)


def upload_catalog_pdf(
    db: Session,
    *,
    contents: bytes,
    original_filename: str,
    supplier_name: str | None = None,
):
    """
    Complete catalog upload flow:

        bytes
          ↓
        save PDF
          ↓
        create import record
          ↓
        extract rows
          ↓
        update import status
          ↓
        commit
    """

    _, stored_path = save_catalog_pdf(
        contents=contents,
        original_filename=original_filename,
    )

    import_record = CatalogImport(
        file_name=original_filename,
        file_path=stored_path,
        supplier_name=supplier_name,
        status="uploaded",
        total_rows=0,
        imported_rows=0,
        failed_rows=0,
    )

    db.add(import_record)
    db.flush()

    try:
        import_record.status = "processing"

        row_count = extract_and_store_pdf_rows(
            db,
            import_id=import_record.id,
            file_path=stored_path,
        )

        import_record.total_rows = row_count
        import_record.status = "extracted"

        db.commit()
        db.refresh(import_record)

        return import_record

    except Exception:
        db.rollback()
        raise


def create_import_record(
    db: Session,
    *,
    file_name: str,
    file_path: str | None = None,
    supplier_name: str | None = None,
    effective_date=None,
):
    """
    Create a catalog import record.

    Transaction ownership remains with the caller.
    """

    return create_catalog_import(
        db=db,
        file_name=file_name,
        file_path=file_path,
        supplier_name=supplier_name,
        effective_date=effective_date,
    )


def get_import(
    db: Session,
    import_id: int,
):
    return get_catalog_import(
        db=db,
        import_id=import_id,
    )


def catalog_item_payload(
    item,
    price=None,
    currency="INR",
):
    """
    Convert a catalog product + latest price
    into an API-friendly dictionary.
    """

    if item is None:
        return None

    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "unit": item.unit,
        "image_url": item.image_url,
        "brand_id": item.brand_id,
        "category_id": item.category_id,
        "price": str(price) if price is not None else None,
        "currency": currency,
    }