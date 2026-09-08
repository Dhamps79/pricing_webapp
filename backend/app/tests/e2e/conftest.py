from decimal import Decimal
import io
import os
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.engine import engine
from app.database.base import Base
from app.database.sessions import SessionLocal, get_db
from app.database.models.brand import Brand
from app.database.models.category import Category
from app.database.models.product import Product
from app.database.models.product_code import ProductCode
from app.database.models.catalog_price import CatalogPrice
from app.database.models.costing_sheet import CostingSheet
from app.database.models.costing_sheet_line import CostingSheetLine


@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """Ensure all database tables exist prior to executing tests."""
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    """TestClient instance for API requests."""
    return TestClient(app)


@pytest.fixture
def db():
    """Provides a transactional database session for test setup and assertions."""
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_valid_pdf_bytes() -> bytes:
    """Returns valid minimal PDF bytes parseable by PDF readers."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
    )


def get_real_sample_pdf_path() -> Path | None:
    """Finds one of the real Siemens sample PDF catalogs in the workspace root if available."""
    candidates = [
        Path("Electrical-Installation-Products-from-A-to-Z-Pricelist-wef-1st-July-2027_compressed.pdf"),
        Path("../Electrical-Installation-Products-from-A-to-Z-Pricelist-wef-1st-July-2027_compressed.pdf"),
        Path("../../Electrical-Installation-Products-from-A-to-Z-Pricelist-wef-1st-July-2027_compressed.pdf"),
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


@pytest.fixture
def test_brand(db: Session) -> Brand:
    """Provides a persistent or newly created Siemens brand."""
    brand = db.query(Brand).filter(Brand.name == "Siemens").first()
    if not brand:
        brand = Brand(name="Siemens", is_active=True)
        db.add(brand)
        db.commit()
        db.refresh(brand)
    return brand


@pytest.fixture
def test_category(db: Session) -> Category:
    """Provides a persistent or newly created MCB category."""
    cat = db.query(Category).filter(Category.name == "MCB").first()
    if not cat:
        cat = Category(name="MCB", is_active=True)
        db.add(cat)
        db.commit()
        db.refresh(cat)
    return cat


@pytest.fixture
def siemens_5sl71057rc_product(db: Session, test_brand: Brand, test_category: Category) -> Product:
    """
    Authoritative reference product: Siemens 5SL71057RC = ₹925.00.
    Directly specified in ORIGINAL_REQUEST.md § Acceptance Criteria and PROJECT.md F5.
    """
    code_str = "5SL71057RC"
    existing_code = db.query(ProductCode).filter(ProductCode.code == code_str).first()
    if existing_code and existing_code.product:
        prod = existing_code.product
    else:
        prod = Product(
            name=code_str,
            description="1P 5SL7 10kA C-Curve MCB 0.5A",
            unit="1 NO",
            brand_id=test_brand.id,
            category_id=test_category.id,
            is_active=True,
        )
        db.add(prod)
        db.flush()

        prod_code = ProductCode(
            product_id=prod.id,
            code=code_str,
            is_primary=True,
        )
        db.add(prod_code)

    # Ensure price is set to exactly 925.00
    price_rec = (
        db.query(CatalogPrice)
        .filter(CatalogPrice.product_id == prod.id)
        .order_by(CatalogPrice.created_at.desc())
        .first()
    )
    if not price_rec or price_rec.price != Decimal("925.00"):
        price_rec = CatalogPrice(
            product_id=prod.id,
            price=Decimal("925.00"),
            currency="INR",
            unit="1 NO",
            standard_package="12",
        )
        db.add(price_rec)

    db.commit()
    db.refresh(prod)
    return prod
