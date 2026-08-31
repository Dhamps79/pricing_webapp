from sqlalchemy.orm import Session

from app.database.models.catalog_import import CatalogImport


def create_catalog_import(
    db: Session,
    *,
    file_name: str,
    file_path: str | None = None,
    supplier_name: str | None = None,
) -> CatalogImport:
    catalog_import = CatalogImport(
        file_name=file_name,
        file_path=file_path,
        supplier_name=supplier_name,
        status="uploaded",
        total_rows=0,
        imported_rows=0,
        failed_rows=0,
    )

    db.add(catalog_import)
    db.flush()

    return catalog_import


def get_catalog_import(
    db: Session,
    import_id: int,
) -> CatalogImport | None:
    return (
        db.query(CatalogImport)
        .filter(CatalogImport.id == import_id)
        .first()
    )


def update_catalog_import_status(
    db: Session,
    *,
    import_id: int,
    status: str,
    error_message: str | None = None,
) -> CatalogImport | None:

    catalog_import = get_catalog_import(
        db,
        import_id,
    )

    if catalog_import is None:
        return None

    catalog_import.status = status
    catalog_import.error_message = error_message

    db.flush()

    return catalog_import