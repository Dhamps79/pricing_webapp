from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.models.costing_sheet import CostingSheet
from app.database.models.costing_sheet_line import CostingSheetLine
from app.repos.catalog_repo import (
    add_costing_line,
    create_costing_sheet,
    delete_costing_line,
    get_costing_sheet,
    latest_prices_for_products,
    list_costing_sheets,
)
from app.repos.product_repo import get_product_by_id


def _line_net(line: CostingSheetLine) -> Decimal:
    discount = (line.discount_percent or Decimal("0")) / Decimal("100")
    unit_net = line.sell_price * (Decimal("1") - discount)
    return (unit_net * line.quantity).quantize(Decimal("0.01"))


def serialize_sheet(sheet: CostingSheet) -> dict:
    lines = []
    list_total = Decimal("0")
    net_total = Decimal("0")

    for line in sheet.lines:
        line_list = (line.list_price * line.quantity).quantize(Decimal("0.01"))
        line_net = _line_net(line)
        list_total += line_list
        net_total += line_net
        product = line.product
        lines.append(
            {
                "id": line.id,
                "product_id": line.product_id,
                "sku": product.sku if product else None,
                "name": product.name if product else "",
                "category": product.category if product else None,
                "quantity": str(line.quantity),
                "unit": line.unit,
                "list_price": str(line.list_price),
                "sell_price": str(line.sell_price),
                "discount_percent": str(line.discount_percent),
                "line_list_total": str(line_list),
                "line_net_total": str(line_net),
                "notes": line.notes,
                "sort_order": line.sort_order,
            }
        )

    sheet_discount = (sheet.discount_percent or Decimal("0")) / Decimal("100")
    grand_total = (net_total * (Decimal("1") - sheet_discount)).quantize(
        Decimal("0.01")
    )

    return {
        "id": sheet.id,
        "title": sheet.title,
        "customer_name": sheet.customer_name,
        "notes": sheet.notes,
        "discount_percent": str(sheet.discount_percent),
        "list_total": str(list_total),
        "net_total": str(net_total),
        "grand_total": str(grand_total),
        "created_at": sheet.created_at,
        "updated_at": sheet.updated_at,
        "lines": lines,
    }


def create_sheet(
    db: Session,
    title: str,
    customer_name: str | None = None,
    notes: str | None = None,
    discount_percent: Decimal = Decimal("0"),
) -> dict:
    sheet = create_costing_sheet(
        db=db,
        title=title,
        customer_name=customer_name,
        notes=notes,
        discount_percent=discount_percent,
    )
    db.commit()
    db.refresh(sheet)
    return serialize_sheet(sheet)


def list_sheets(db: Session) -> list[dict]:
    sheets = list_costing_sheets(db)
    return [
        {
            "id": sheet.id,
            "title": sheet.title,
            "customer_name": sheet.customer_name,
            "discount_percent": str(sheet.discount_percent),
            "updated_at": sheet.updated_at,
            "line_count": len(sheet.lines),
        }
        for sheet in sheets
    ]


def get_sheet(db: Session, sheet_id: int) -> dict | None:
    sheet = get_costing_sheet(db, sheet_id)
    if sheet is None:
        return None
    return serialize_sheet(sheet)


def update_sheet(
    db: Session,
    sheet_id: int,
    title: str | None = None,
    customer_name: str | None = None,
    notes: str | None = None,
    discount_percent: Decimal | None = None,
) -> dict | None:
    sheet = get_costing_sheet(db, sheet_id)
    if sheet is None:
        return None
    if title is not None:
        sheet.title = title
    if customer_name is not None:
        sheet.customer_name = customer_name
    if notes is not None:
        sheet.notes = notes
    if discount_percent is not None:
        sheet.discount_percent = discount_percent
    db.commit()
    return serialize_sheet(get_costing_sheet(db, sheet_id))


def add_product_to_sheet(
    db: Session,
    sheet_id: int,
    product_id: int,
    quantity: Decimal = Decimal("1"),
    sell_price: Decimal | None = None,
    discount_percent: Decimal = Decimal("0"),
    notes: str | None = None,
) -> dict | None:
    sheet = get_costing_sheet(db, sheet_id)
    product = get_product_by_id(db, product_id)
    if sheet is None or product is None:
        return None

    prices = latest_prices_for_products(db, [product.id])
    latest = prices.get(product.id)
    list_price = latest.price if latest else Decimal("0")
    unit_sell = sell_price if sell_price is not None else list_price

    add_costing_line(
        db=db,
        sheet=sheet,
        product=product,
        quantity=quantity,
        list_price=list_price,
        sell_price=unit_sell,
        discount_percent=discount_percent,
        unit=product.unit,
        notes=notes,
        sort_order=len(sheet.lines),
    )
    db.commit()
    return serialize_sheet(get_costing_sheet(db, sheet_id))


def update_line(
    db: Session,
    sheet_id: int,
    line_id: int,
    quantity: Decimal | None = None,
    sell_price: Decimal | None = None,
    discount_percent: Decimal | None = None,
    notes: str | None = None,
) -> dict | None:
    sheet = get_costing_sheet(db, sheet_id)
    if sheet is None:
        return None

    line = next((item for item in sheet.lines if item.id == line_id), None)
    if line is None:
        return None

    if quantity is not None:
        line.quantity = quantity
    if sell_price is not None:
        line.sell_price = sell_price
    if discount_percent is not None:
        line.discount_percent = discount_percent
    if notes is not None:
        line.notes = notes

    db.commit()
    return serialize_sheet(get_costing_sheet(db, sheet_id))


def remove_line(db: Session, sheet_id: int, line_id: int) -> dict | None:
    sheet = get_costing_sheet(db, sheet_id)
    if sheet is None:
        return None
    line = next((item for item in sheet.lines if item.id == line_id), None)
    if line is None:
        return None
    delete_costing_line(db, line.id)
    db.commit()
    return serialize_sheet(get_costing_sheet(db, sheet_id))


def delete_sheet(db: Session, sheet_id: int) -> bool:
    sheet = get_costing_sheet(db, sheet_id)
    if sheet is None:
        return False
    db.delete(sheet)
    db.commit()
    return True
