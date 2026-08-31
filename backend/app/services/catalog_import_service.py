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
from app.services.catalog_parser_service import (
    parse_catalog_import_rows,
)
items = parse_catalog_import_rows(rows)


CATALOG_STORAGE_DIR = Path("storage/catalog")


def save_catalog_pdf(
    *,
    contents: bytes,
    original_filename: str,
) -> tuple[str, str]:
    """
    Save uploaded PDF to catalog storage.

    Returns:
        (stored_filename, stored_path)
    """

    CATALOG_STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    suffix = Path(original_filename).suffix.lower()

    if suffix != ".pdf":
        raise ValueError("Only PDF files are supported.")

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
    Extract PDF text and store each extracted row
    in catalog_import_rows.

    Returns:
        Number of raw rows created.
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
    Complete PDF ingestion pipeline.

    1. Save PDF
    2. Create catalog_imports record
    3. Extract PDF text
    4. Store raw rows
    """

    stored_filename, stored_path = save_catalog_pdf(
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
        import_record.imported_rows = row_count
        import_record.status = "extracted"

    except Exception as exc:
        import_record.status = "failed"
        import_record.error_message = str(exc)

        db.commit()

        raise

    db.commit()
    db.refresh(import_record)

    return import_record


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
    """
    Retrieve a catalog import by ID.
    """

    return get_catalog_import(
        db=db,
        import_id=import_id,
    )


def catalog_item_payload(item):
    """
    Convert a Product ORM object into a JSON-safe dictionary.
    """

    if item is None:
        return None

    return {
        "id": item.id,
        "name": item.name,
        "sku": getattr(item, "sku", None),
        "description": getattr(item, "description", None),
        "unit": getattr(item, "unit", None),
        "image_url": getattr(item, "image_url", None),
        "brand_id": getattr(item, "brand_id", None),
        "category_id": getattr(item, "category_id", None),
    }


def import_pricelists(
    db: Session,
    *,
    import_id: int,
):
    """
    Placeholder for the structured price-list import stage.
    """

    raise NotImplementedError(
        "Price-list import processing has not been implemented yet."
    )