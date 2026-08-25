from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.database.models.product import Product
from app.repos.catalog_repo import get_source_for_product_url
from app.repos.price_history_repo import create_price_history
from app.repos.product_repo import create_product, get_product_by_sku
from app.repos.source_repo import create_source
from app.services.pricelist_parser import parse_pricelist_pdf

PRICELIST_FILES = [
    (
        "Electrical Installation Products from A to Z",
        "Electrical-Installation-Products-from-A-to-Z-Pricelist-wef-1st-July-2027.pdf",
    ),
    (
        "Low Voltage Control Products",
        "Low-Voltage-Control-Products_Pricelist_w.e.f_01st_Jul_2026-1.pdf",
    ),
    (
        "Low Voltage Power Distribution Products",
        "Low-Voltage-Power-Distribution-Products-Pricelist-w.e.f-1st-Jul-2026-1.pdf",
    ),
]


def default_pricelist_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def import_pricelists(
    db: Session,
    directory: str | Path | None = None,
) -> dict:
    from app.database.schema import ensure_schema

    ensure_schema()
    root = Path(directory) if directory else default_pricelist_dir()
    fetched_at = datetime.now(timezone.utc)
    created = 0
    updated = 0
    skipped = 0
    files = 0

    for title, filename in PRICELIST_FILES:
        pdf_path = root / filename
        if not pdf_path.exists():
            skipped += 1
            continue

        files += 1
        source_url = pdf_path.resolve().as_uri()
        items = parse_pricelist_pdf(pdf_path, title)

        for item in items:
            product = get_product_by_sku(db, item.sku)
            if product is None:
                product = create_product(
                    db=db,
                    name=item.name,
                    image_url=None,
                    sku=item.sku,
                    category=item.category,
                    unit=item.unit,
                    description=item.description,
                )
                created += 1
            else:
                product.name = item.name
                product.category = item.category
                product.unit = item.unit or product.unit
                product.description = item.description
                updated += 1

            source = get_source_for_product_url(db, product.id, source_url)
            if source is None:
                source = create_source(
                    db=db,
                    product_id=product.id,
                    url=source_url,
                    domain=item.source_file,
                    source_type="pricelist_pdf",
                )

            create_price_history(
                db=db,
                product_id=product.id,
                source_id=source.id,
                price=Decimal(str(item.list_price)),
                currency="INR",
                availability=f"page {item.page}",
                fetched_at=fetched_at,
            )

        db.flush()

    db.commit()
    return {
        "files_imported": files,
        "products_created": created,
        "products_updated": updated,
        "files_missing": skipped,
    }


def catalog_item_payload(product: Product, price, currency: str | None) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "unit": product.unit,
        "list_price": str(price) if price is not None else None,
        "currency": currency,
    }
