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
        .where(Product.sku.is_not(None))
        .order_by(Product.category, Product.sku)
        .offset(offset)
        .limit(limit)
    )

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

    return list(db.scalars(statement).all())


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
        select(Product.category)
        .where(Product.category.is_not(None), Product.sku.is_not(None))
        .distinct()
        .order_by(Product.category)
    )
    return [row[0] for row in db.execute(statement).all() if row[0]]


def latest_prices_for_products(
    db: Session,
    product_ids: list[int],
) -> dict[int, PriceHistory]:
    if not product_ids:
        return {}

    rank = (
        select(
            PriceHistory.id,
            PriceHistory.product_id,
            PriceHistory.price,
            PriceHistory.currency,
            PriceHistory.fetched_at,
            func.row_number()
            .over(
                partition_by=PriceHistory.product_id,
                order_by=PriceHistory.fetched_at.desc(),
            )
            .label("row_number"),
        )
        .where(PriceHistory.product_id.in_(product_ids))
        .subquery()
    )

    rows = db.execute(
        select(
            rank.c.id,
            rank.c.product_id,
            rank.c.price,
            rank.c.currency,
            rank.c.fetched_at,
        ).where(rank.c.row_number == 1)
    ).all()

    latest: dict[int, PriceHistory] = {}
    for row in rows:
        history = PriceHistory(
            id=row.id,
            product_id=row.product_id,
            price=row.price,
            currency=row.currency,
            fetched_at=row.fetched_at,
        )
        latest[row.product_id] = history
    return latest


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
