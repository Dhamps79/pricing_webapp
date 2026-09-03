from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.models.costing_sheet import CostingSheet
from app.database.models.costing_sheet_line import CostingSheetLine
from app.database.models.price_history import PriceHistory
from app.database.models.product import Product
from app.database.models.source import Source
from app.database.models.catalog_import import CatalogImport
from app.database.models.catalog_import_row import CatalogImportRow
from app.database.models.catalog_price import CatalogPrice
from app.database.models.catalog_import_row import CatalogImportRow
from app.database.models.category import Category
from app.database.models.product import Product
from app.database.models.product_code import ProductCode


def create_catalog_import(
    db: Session,
    *,
    file_name: str,
    file_path: str | None = None,
    supplier_name: str | None = None,
    effective_date=None,
):
    import_record = CatalogImport(
        file_name=file_name,
        file_path=file_path,
        supplier_name=supplier_name,
        effective_date=effective_date,
        status="uploaded",
        total_rows=0,
        imported_rows=0,
        failed_rows=0,
    )

    db.add(import_record)
    db.commit()
    db.refresh(import_record)

    return import_record
    return import_record


def create_catalog_import_row(
    db,
    *,
    import_id: int,
    page_number: int | None,
    row_number: int | None,
    raw_text: str,
):
    row = CatalogImportRow(
        import_id=import_id,
        page_number=page_number,
        row_number=row_number,
        raw_text=raw_text,
        parsed_status="pending",
    )

    db.add(row)

    return row

def get_catalog_import(
    db: Session,
    *,
    import_id: int,
):
    """
    Retrieve a catalog import by ID.
    """

    return (
        db.query(CatalogImport)
        .filter(CatalogImport.id == import_id)
        .first()
    )


def search_catalog(
    db: Session,
    query: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:

    statement = (
        select(Product)
        .join(
            ProductCode,
            ProductCode.product_id == Product.id,
            isouter=True,
        )
        .join(
            Category,
            Category.id == Product.category_id,
            isouter=True,
        )
        .options(
            selectinload(Product.codes),
            selectinload(Product.category),
            selectinload(Product.brand),
        )
        .where(Product.is_active.is_(True))
        .distinct()
        .order_by(Product.name)
        .offset(offset)
        .limit(limit)
    )

    if query:
        pattern = f"%{query.strip()}%"

        statement = statement.where(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                ProductCode.code.ilike(pattern),
            )
        )

    if category:
        statement = statement.where(
            Category.name == category
        )

    return list(
        db.scalars(statement).unique().all()
    )


def count_catalog(
    db: Session,
    query: str | None = None,
    category: str | None = None,
) -> int:
    statement = select(func.count(Product.id)).where(Product.sku.is_not(None))

    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                Product.sku.ilike(pattern),
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                Product.category.ilike(pattern),
            )
        )

    if category:
        statement = statement.where(Product.category == category)

    return int(db.scalar(statement) or 0)


def list_categories(db: Session) -> list[str]:

    statement = (
        select(Category.name)
        .join(
            Product,
            Product.category_id == Category.id,
        )
        .where(
            Product.is_active.is_(True),
            Category.is_active.is_(True),
        )
        .distinct()
        .order_by(Category.name)
    )

    return list(
        db.scalars(statement).all()
    )

def latest_catalog_prices_for_products(
    db: Session,
    product_ids: list[int],
) -> dict[int, CatalogPrice]:

    if not product_ids:
        return {}

    ranked = (
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
                order_by=(
                    CatalogPrice.created_at.desc(),
                    CatalogPrice.id.desc(),
                ),
            )
            .label("rn"),
        )
        .where(
            CatalogPrice.product_id.in_(product_ids)
        )
        .subquery()
    )

    rows = db.execute(
        select(
            ranked.c.id,
            ranked.c.product_id,
            ranked.c.price,
            ranked.c.currency,
            ranked.c.unit,
            ranked.c.standard_package,
            ranked.c.created_at,
        ).where(
            ranked.c.rn == 1
        )
    ).all()

    return {
        row.product_id: CatalogPrice(
            id=row.id,
            product_id=row.product_id,
            price=row.price,
            currency=row.currency,
            unit=row.unit,
            standard_package=row.standard_package,
            created_at=row.created_at,
        )
        for row in rows
    }


def list_costing_sheets(db: Session) -> list[CostingSheet]:
    statement = (
        select(CostingSheet)
        .options(selectinload(CostingSheet.lines))
        .order_by(CostingSheet.updated_at.desc())
    )
    return list(db.scalars(statement).all())


def get_costing_sheet(
    db: Session,
    sheet_id: int,
) -> CostingSheet | None:
    statement = (
        select(CostingSheet)
        .options(
            selectinload(CostingSheet.lines).selectinload(CostingSheetLine.product)
        )
        .where(CostingSheet.id == sheet_id)
    )
    return db.scalar(statement)


def create_costing_sheet(
    db: Session,
    title: str,
    customer_name: str | None,
    notes: str | None,
    discount_percent: Decimal,
) -> CostingSheet:
    sheet = CostingSheet(
        title=title,
        customer_name=customer_name,
        notes=notes,
        discount_percent=discount_percent,
    )
    db.add(sheet)
    db.flush()
    return sheet


def add_costing_line(
    db: Session,
    sheet: CostingSheet,
    product: Product,
    quantity: Decimal,
    list_price: Decimal,
    sell_price: Decimal,
    discount_percent: Decimal,
    unit: str | None,
    notes: str | None,
    sort_order: int,
) -> CostingSheetLine:
    line = CostingSheetLine(
        costing_sheet_id=sheet.id,
        product_id=product.id,
        quantity=quantity,
        list_price=list_price,
        sell_price=sell_price,
        discount_percent=discount_percent,
        unit=unit,
        notes=notes,
        sort_order=sort_order,
    )
    db.add(line)
    db.flush()
    return line


def delete_costing_line(
    db: Session,
    line_id: int,
) -> CostingSheetLine | None:
    line = db.get(CostingSheetLine, line_id)
    if line is None:
        return None
    db.delete(line)
    db.flush()
    return line


def get_source_for_product_url(
    db: Session,
    product_id: int,
    url: str,
) -> Source | None:
    statement = select(Source).where(
        Source.product_id == product_id,
        Source.url == url,
    )
    return db.scalar(statement)
