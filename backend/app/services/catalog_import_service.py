from sqlalchemy.orm import Session

from app.repos.catalog_import_repo import (
    create_catalog_import,
    get_catalog_import,
)


def create_import_record(
    db: Session,
    *,
    file_name: str,
    file_path: str,
    supplier_name: str | None = None,
):
    """
    Create a catalog import record.

    This represents the uploaded source file before
    its contents are parsed/imported.
    """

    return create_catalog_import(
        db=db,
        file_name=file_name,
        file_path=file_path,
        supplier_name=supplier_name,
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

    Used by the catalog API when returning products.
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
    Import price-list rows belonging to a catalog import.

    PDF parsing/import logic will be implemented here in the
    next stage.

    For now this function exists to preserve the existing
    catalog API contract.
    """

    raise NotImplementedError(
        "Price-list import processing has not been implemented yet."
    )