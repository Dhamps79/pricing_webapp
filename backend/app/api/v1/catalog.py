from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database.models.catalog_price import CatalogPrice
from app.database.models.category import Category
from app.database.models.product import Product
from app.database.models.product_code import ProductCode
from app.database.sessions import get_db
from app.services.catalog_import_service import (
    catalog_item_payload,
    upload_catalog_pdf,
)


router = APIRouter(
    prefix="/catalog",
    tags=["Catalog"],
)


# ---------------------------------------------------------------------------
# Catalog PDF import
# ---------------------------------------------------------------------------


@router.post("/imports/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    supplier_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Upload a catalog PDF and import its products/prices.
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
        db.rollback()

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
        "completed_at": import_record.completed_at,
    }


# ---------------------------------------------------------------------------
# Catalog products
# ---------------------------------------------------------------------------


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
    Search products imported from catalogs.

    Catalog prices come from CatalogPrice.

    This endpoint intentionally does NOT use PriceHistory.
    PriceHistory belongs to online website price tracking.
    """

    statement = (
        select(Product)
        .outerjoin(ProductCode, ProductCode.product_id == Product.id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(Product.is_active.is_(True))
        .distinct()
    )

    if q:
        pattern = f"%{q.strip()}%"

        statement = statement.where(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                ProductCode.code.ilike(pattern),
                Category.name.ilike(pattern),
            )
        )

    if category:
        statement = statement.where(
            Category.name.ilike(category.strip())
        )

    statement = (
        statement
        .order_by(Product.name.asc())
        .offset(offset)
        .limit(limit)
    )

    products = list(db.scalars(statement).unique().all())

    product_ids = [product.id for product in products]

    prices = _latest_catalog_prices(
        db,
        product_ids,
    )

    items = []

    for product in products:
        latest_price = prices.get(product.id)

        items.append(
            catalog_item_payload(
                product,
                latest_price.price if latest_price else None,
                latest_price.currency if latest_price else "INR",
            )
        )

    count_statement = (
        select(func.count(func.distinct(Product.id)))
        .select_from(Product)
        .outerjoin(
            ProductCode,
            ProductCode.product_id == Product.id,
        )
        .outerjoin(
            Category,
            Category.id == Product.category_id,
        )
        .where(Product.is_active.is_(True))
    )

    if q:
        pattern = f"%{q.strip()}%"

        count_statement = count_statement.where(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                ProductCode.code.ilike(pattern),
                Category.name.ilike(pattern),
            )
        )

    if category:
        count_statement = count_statement.where(
            Category.name.ilike(category.strip())
        )

    total = int(db.scalar(count_statement) or 0)

    return {
        "total": total,
        "items": items,
    }


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@router.get("/categories")
def get_catalog_categories(
    db: Session = Depends(get_db),
):
    """
    Return categories that currently contain active catalog products.
    """

    statement = (
        select(Category.name)
        .join(
            Product,
            Product.category_id == Category.id,
        )
        .where(
            Category.is_active.is_(True),
            Product.is_active.is_(True),
        )
        .distinct()
        .order_by(Category.name.asc())
    )

    categories = [
        row[0]
        for row in db.execute(statement).all()
        if row[0]
    ]

    return {
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# Catalog imports
# ---------------------------------------------------------------------------


@router.get("/imports/{import_id}")
def get_catalog_import_status(
    import_id: int,
    db: Session = Depends(get_db),
):
    """
    Return the status of a catalog import.
    """

    from app.database.models.catalog_import import CatalogImport

    import_record = db.get(
        CatalogImport,
        import_id,
    )

    if import_record is None:
        raise HTTPException(
            status_code=404,
            detail="Catalog import not found.",
        )

    return {
        "id": import_record.id,
        "file_name": import_record.file_name,
        "supplier_name": import_record.supplier_name,
        "effective_date": import_record.effective_date,
        "status": import_record.status,
        "total_rows": import_record.total_rows,
        "imported_rows": import_record.imported_rows,
        "failed_rows": import_record.failed_rows,
        "error_message": import_record.error_message,
        "created_at": import_record.created_at,
        "completed_at": import_record.completed_at,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _latest_catalog_prices(
    db: Session,
    product_ids: list[int],
) -> dict[int, CatalogPrice]:
    """
    Get the latest CatalogPrice for each product.

    IMPORTANT:
    This is intentionally CatalogPrice, NOT PriceHistory.

    CatalogPrice = price printed/imported from a PDF catalog.
    PriceHistory = price fetched from an online source.
    """

    if not product_ids:
        return {}

    ranked_prices = (
        select(
            CatalogPrice.id,
            CatalogPrice.product_id,
            CatalogPrice.price,
            CatalogPrice.currency,
            CatalogPrice.unit,
            CatalogPrice.standard_package,
            CatalogPrice.created_at,
            func.row_number()
            .over(
                partition_by=CatalogPrice.product_id,
                order_by=CatalogPrice.created_at.desc(),
            )
            .label("row_number"),
        )
        .where(
            CatalogPrice.product_id.in_(product_ids)
        )
        .subquery()
    )

    rows = db.execute(
        select(
            ranked_prices.c.id,
            ranked_prices.c.product_id,
            ranked_prices.c.price,
            ranked_prices.c.currency,
            ranked_prices.c.unit,
            ranked_prices.c.standard_package,
            ranked_prices.c.created_at,
        ).where(
            ranked_prices.c.row_number == 1
        )
    ).all()

    latest: dict[int, CatalogPrice] = {}

    for row in rows:
        catalog_price = CatalogPrice(
            id=row.id,
            product_id=row.product_id,
            price=row.price,
            currency=row.currency,
            unit=row.unit,
            standard_package=row.standard_package,
            created_at=row.created_at,
        )

        latest[row.product_id] = catalog_price

    return latest