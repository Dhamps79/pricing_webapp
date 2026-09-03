from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models.brand import Brand
from app.database.models.catalog_import import CatalogImport
from app.database.models.catalog_import_row import CatalogImportRow
from app.database.models.catalog_price import CatalogPrice
from app.database.models.category import Category
from app.database.models.product import Product
from app.database.models.product_attribute import ProductAttribute
from app.database.models.product_code import ProductCode
from app.services.parser.siemens_parser import (
    ParsedCatalogProduct,
    parse_siemens_pdf,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Storage configuration
# ---------------------------------------------------------------------------

CATALOG_STORAGE_DIR = Path("storage/catalog")

MAX_CATALOG_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# File storage
# ---------------------------------------------------------------------------


def save_catalog_pdf(
    *,
    contents: bytes,
    original_filename: str,
) -> tuple[str, str]:
    """
    Save an uploaded catalog PDF.

    The original filename is never used as the storage filename.
    """

    if not original_filename:
        raise ValueError(
            "Filename is required."
        )

    if Path(original_filename).suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    if not contents:
        raise ValueError(
            "Uploaded PDF is empty."
        )

    if len(contents) > MAX_CATALOG_FILE_SIZE:
        raise ValueError(
            "Catalog PDF exceeds the maximum allowed size."
        )

    CATALOG_STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = (
        f"{uuid4().hex}.pdf"
    )

    stored_path = (
        CATALOG_STORAGE_DIR
        / stored_filename
    )

    stored_path.write_bytes(contents)

    return (
        stored_filename,
        str(stored_path),
    )


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------


def get_or_create_brand(
    db: Session,
    *,
    name: str,
) -> Brand:
    normalized_name = name.strip()

    if not normalized_name:
        raise ValueError(
            "Brand name cannot be empty."
        )

    brand = db.scalar(
        select(Brand).where(
            Brand.name == normalized_name
        )
    )

    if brand:
        return brand

    brand = Brand(
        name=normalized_name,
        is_active=True,
    )

    db.add(brand)
    db.flush()

    return brand


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------


def get_or_create_category(
    db: Session,
    *,
    name: str,
) -> Category:
    normalized_name = name.strip()

    if not normalized_name:
        raise ValueError(
            "Category name cannot be empty."
        )

    category = db.scalar(
        select(Category).where(
            Category.name == normalized_name
        )
    )

    if category:
        return category

    category = Category(
        name=normalized_name,
        is_active=True,
    )

    db.add(category)
    db.flush()

    return category


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


def get_product_by_code(
    db: Session,
    *,
    code: str,
) -> Product | None:
    statement = (
        select(Product)
        .join(
            ProductCode,
            ProductCode.product_id == Product.id,
        )
        .where(
            ProductCode.code == code
        )
    )

    return db.scalar(statement)


def create_product(
    db: Session,
    *,
    parsed: ParsedCatalogProduct,
) -> Product:
    brand = get_or_create_brand(
        db,
        name=parsed.brand,
    )

    category = None

    if parsed.category:
        category = get_or_create_category(
            db,
            name=parsed.category,
        )

    product = Product(
        name=(
            parsed.description
            or parsed.product_code
        ),
        brand_id=brand.id,
        category_id=(
            category.id
            if category
            else None
        ),
        unit=parsed.unit,
        is_active=True,
    )

    db.add(product)
    db.flush()

    product_code = ProductCode(
        product_id=product.id,
        code=parsed.product_code,
        code_type="manufacturer",
        is_primary=True,
    )

    db.add(product_code)

    return product


def update_product_metadata(
    db: Session,
    *,
    product: Product,
    parsed: ParsedCatalogProduct,
) -> None:
    """
    Update only catalog-owned metadata.

    We deliberately do not overwrite a manually maintained product name
    when one already exists.
    """

    if not product.name and parsed.description:
        product.name = parsed.description

    if not product.unit and parsed.unit:
        product.unit = parsed.unit

    if parsed.brand:
        brand = get_or_create_brand(
            db,
            name=parsed.brand,
        )

        if product.brand_id is None:
            product.brand_id = brand.id

    if parsed.category:
        category = get_or_create_category(
            db,
            name=parsed.category,
        )

        if product.category_id is None:
            product.category_id = category.id


# ---------------------------------------------------------------------------
# Product attributes
# ---------------------------------------------------------------------------


def store_product_attributes(
    db: Session,
    *,
    product: Product,
    parsed: ParsedCatalogProduct,
) -> None:
    for attribute_name, attribute_value in (
        parsed.attributes
    ):
        existing = db.scalar(
            select(ProductAttribute).where(
                ProductAttribute.product_id
                == product.id,
                ProductAttribute.attribute_name
                == attribute_name,
            )
        )

        if existing:
            existing.attribute_value = (
                attribute_value
            )
            continue

        db.add(
            ProductAttribute(
                product_id=product.id,
                attribute_name=attribute_name,
                attribute_value=attribute_value,
            )
        )


# ---------------------------------------------------------------------------
# Catalog price
# ---------------------------------------------------------------------------


def store_catalog_price(
    db: Session,
    *,
    product: Product,
    import_id: int,
    parsed: ParsedCatalogProduct,
) -> CatalogPrice:
    catalog_price = CatalogPrice(
        product_id=product.id,
        import_id=import_id,
        price=parsed.price,
        currency="INR",
        unit=parsed.unit,
        standard_package=(
            parsed.standard_package
        ),
    )

    db.add(catalog_price)

    return catalog_price


# ---------------------------------------------------------------------------
# Import row
# ---------------------------------------------------------------------------


def build_import_row_text(
    parsed: ParsedCatalogProduct,
) -> str:
    parts = [
        parsed.product_code,
    ]

    if parsed.description:
        parts.append(
            parsed.description
        )

    if parsed.price is not None:
        parts.append(
            f"MRP={parsed.price}"
        )

    if parsed.standard_package:
        parts.append(
            f"STD_PKG={parsed.standard_package}"
        )

    return " | ".join(parts)


def create_import_row(
    db: Session,
    *,
    import_id: int,
    parsed: ParsedCatalogProduct,
    row_number: int,
) -> CatalogImportRow:
    row = CatalogImportRow(
        import_id=import_id,
        page_number=parsed.page_number,
        row_number=row_number,
        raw_text=build_import_row_text(
            parsed
        ),
        parsed_status="imported",
    )

    db.add(row)

    return row


# ---------------------------------------------------------------------------
# Single product import
# ---------------------------------------------------------------------------


def import_parsed_product(
    db: Session,
    *,
    import_id: int,
    parsed: ParsedCatalogProduct,
) -> Product:
    """
    Upsert one normalized catalog product.
    """

    product = get_product_by_code(
        db,
        code=parsed.product_code,
    )

    if product is None:
        product = create_product(
            db,
            parsed=parsed,
        )
    else:
        update_product_metadata(
            db,
            product=product,
            parsed=parsed,
        )

    store_product_attributes(
        db,
        product=product,
        parsed=parsed,
    )

    store_catalog_price(
        db,
        product=product,
        import_id=import_id,
        parsed=parsed,
    )

    return product


# ---------------------------------------------------------------------------
# Full PDF import
# ---------------------------------------------------------------------------


def import_siemens_catalog(
    db: Session,
    *,
    import_record: CatalogImport,
) -> CatalogImport:
    """
    Parse and persist a Siemens catalog.

    Transaction ownership belongs to this function's caller.
    """

    if not import_record.file_path:
        raise ValueError(
            "Catalog import has no file path."
        )

    import_record.status = "processing"

    try:
        parsed_products = parse_siemens_pdf(
            import_record.file_path
        )

        import_record.total_rows = (
            len(parsed_products)
        )

        imported_count = 0
        failed_count = 0

        for index, parsed in enumerate(
            parsed_products,
            start=1,
        ):
            try:
                with db.begin_nested():
                    import_parsed_product(
                        db,
                        import_id=import_record.id,
                        parsed=parsed,
                        )
                    create_import_row(
                        db,
                        import_id=import_record.id,
                        parsed=parsed,
                        row_number=index,
                        )
                    imported_count += 1

            except Exception:
                failed_count += 1
                logger.exception(
                    "Failed to import catalog product",
                    extra={
                        "import_id": import_record.id,
                        "product_code": parsed.product_code,
                        "page_number": parsed.page_number,
                        },
                )
                db.add(
                    CatalogImportRow(
                        import_id=import_record.id,
                        page_number=parsed.page_number,
                        row_number=index,
                        raw_text=build_import_row_text(
                            parsed
                        ),
                        parsed_status="failed",
                        error_message=(
                            "Catalog row could not be imported."
                            ),
                    )
                )

        import_record.imported_rows = (
            imported_count
        )

        import_record.failed_rows = (
            failed_count
        )

        if failed_count:
            import_record.status = "completed_with_errors"
        else:
            import_record.status = "completed"

        import_record.completed_at = (
            datetime.utcnow()
        )

        return import_record

    except Exception as exc:
        import_record.status = "failed"
        import_record.error_message = (
            "Catalog import failed."
        )

        import_record.completed_at = (
            datetime.utcnow()
        )

        logger.exception(
            "Catalog import failed",
            extra={
                "import_id": import_record.id,
            },
        )

        raise exc


# ---------------------------------------------------------------------------
# Public upload entry point
# ---------------------------------------------------------------------------


def upload_catalog_pdf(
    db: Session,
    *,
    contents: bytes,
    original_filename: str,
    supplier_name: str | None = None,
    effective_date=None,
) -> CatalogImport:
    """
    Complete catalog upload:

        bytes
          ↓
        local PDF storage
          ↓
        CatalogImport
          ↓
        coordinate-aware Siemens parser
          ↓
        Product / ProductCode / Category / Brand
          ↓
        ProductAttribute
          ↓
        CatalogPrice
          ↓
        CatalogImportRow
    """

    _, stored_path = save_catalog_pdf(
        contents=contents,
        original_filename=original_filename,
    )

    import_record = CatalogImport(
        file_name=original_filename,
        file_path=stored_path,
        supplier_name=supplier_name or "Siemens",
        effective_date=effective_date,
        status="uploaded",
        total_rows=0,
        imported_rows=0,
        failed_rows=0,
    )

    db.add(import_record)
    db.flush()

    try:
        import_siemens_catalog(
            db,
            import_record=import_record,
        )

        db.commit()
        db.refresh(import_record)

        return import_record

    except Exception:
        db.rollback()

        # The database transaction has failed, so the uploaded file should
        # not remain as an apparently valid catalog artifact.
        try:
            Path(stored_path).unlink(
                missing_ok=True
            )
        except OSError:
            logger.exception(
                "Unable to remove failed catalog file",
                extra={
                    "path": stored_path,
                },
            )

        raise


# ---------------------------------------------------------------------------
# Compatibility helpers
# ---------------------------------------------------------------------------


def create_import_record(
    db: Session,
    *,
    file_name: str,
    file_path: str | None = None,
    supplier_name: str | None = None,
    effective_date=None,
) -> CatalogImport:
    """
    Create an import record without starting the import.

    Transaction ownership remains with the caller.
    """

    record = CatalogImport(
        file_name=file_name,
        file_path=file_path,
        supplier_name=supplier_name,
        effective_date=effective_date,
        status="uploaded",
        total_rows=0,
        imported_rows=0,
        failed_rows=0,
    )

    db.add(record)
    db.flush()

    return record


def get_import(
    db: Session,
    import_id: int,
) -> CatalogImport | None:
    return db.get(
        CatalogImport,
        import_id,
    )


def catalog_item_payload(
    item: Product | None,
    *,
    price=None,
    currency: str = "INR",
) -> dict | None:
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
        "price": (
            str(price)
            if price is not None
            else None
        ),
        "currency": currency,
    }