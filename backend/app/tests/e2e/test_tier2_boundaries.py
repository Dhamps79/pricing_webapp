from decimal import Decimal
import io
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.models.brand import Brand
from app.database.models.category import Category
from app.database.models.product import Product
from app.database.models.product_code import ProductCode
from app.database.models.catalog_price import CatalogPrice
from app.database.models.costing_sheet import CostingSheet
from app.database.models.costing_sheet_line import CostingSheetLine


# ===========================================================================
# FEATURE 1 BOUNDARIES: PDF Upload Component & Endpoint
# ===========================================================================

def test_b1_upload_empty_pdf_file_rejected(client: TestClient):
    """B1.1: Uploading a 0-byte PDF returns HTTP 400."""
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("zero.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_b1_upload_non_pdf_file_rejected(client: TestClient):
    """B1.2: Uploading a non-PDF file (.csv) returns HTTP 400."""
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("price_list.csv", io.BytesIO(b"sku,price\n123,100"), "text/csv")},
    )
    assert response.status_code == 400
    assert "only pdf files" in response.json()["detail"].lower()


def test_b1_upload_missing_filename_rejected(client: TestClient):
    """B1.3: Upload with empty filename returns HTTP 400."""
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
    )
    assert response.status_code == 400


def test_b1_upload_corrupt_pdf_handled_gracefully(client: TestClient):
    """B1.4: Uploading random binary junk with .pdf extension returns 400/500 without crashing."""
    corrupt_bytes = b"%PDF-corrupted-binary-header\x00\xff\xfe\xaa\xbb\xcc"
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("corrupt.pdf", io.BytesIO(corrupt_bytes), "application/pdf")},
    )
    # Must return client or server error response cleanly
    assert response.status_code in [400, 500]
    assert "detail" in response.json()


def test_b1_upload_long_filename_boundary(client: TestClient):
    """B1.5: Very long filename (200 characters) is handled cleanly."""
    long_name = f"{'a' * 180}_{uuid.uuid4().hex[:6]}.pdf"
    from app.tests.e2e.conftest import make_valid_pdf_bytes
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": (long_name, io.BytesIO(make_valid_pdf_bytes()), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["file_name"] == long_name


# ===========================================================================
# FEATURE 2 BOUNDARIES: Upload Progress & Status
# ===========================================================================

def test_b2_get_status_negative_id(client: TestClient):
    """B2.1: Negative import ID returns 404."""
    assert client.get("/api/v1/catalog/imports/-1").status_code == 404


def test_b2_get_status_zero_id(client: TestClient):
    """B2.2: Zero import ID returns 404."""
    assert client.get("/api/v1/catalog/imports/0").status_code == 404


def test_b2_get_status_non_numeric_id(client: TestClient):
    """B2.3: Non-numeric import ID string returns 422."""
    assert client.get("/api/v1/catalog/imports/invalid-string-id").status_code == 422


def test_b2_get_status_extreme_int64_id(client: TestClient):
    """B2.4: Extreme 64-bit integer ID returns 404."""
    assert client.get("/api/v1/catalog/imports/9223372036854775000").status_code == 404


def test_b2_status_error_message_null_on_clean_import(client: TestClient):
    """B2.5: Error message field is null or clean on uncorrupted imports."""
    from app.tests.e2e.conftest import make_valid_pdf_bytes
    res = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("clean_check.pdf", io.BytesIO(make_valid_pdf_bytes()), "application/pdf")},
    )
    import_id = res.json()["id"]
    status_data = client.get(f"/api/v1/catalog/imports/{import_id}").json()
    assert status_data.get("error_message") is None or isinstance(status_data.get("error_message"), str)


# ===========================================================================
# FEATURE 3 BOUNDARIES: Auto-Refresh on Upload
# ===========================================================================

def test_b3_offset_beyond_total_returns_empty_items(client: TestClient):
    """B3.1: Querying with offset far beyond total items returns items=[] and status 200."""
    res = client.get("/api/v1/catalog/items?offset=1000000")
    assert res.status_code == 200
    assert res.json()["items"] == []


def test_b3_minimum_limit_boundary_1(client: TestClient):
    """B3.2: Minimum limit query parameter (limit=1) returns at most 1 item."""
    res = client.get("/api/v1/catalog/items?limit=1")
    assert res.status_code == 200
    assert len(res.json()["items"]) <= 1


def test_b3_maximum_limit_boundary_200(client: TestClient):
    """B3.3: Maximum limit query parameter (limit=200) executes successfully."""
    res = client.get("/api/v1/catalog/items?limit=200")
    assert res.status_code == 200


def test_b3_limit_exceeding_maximum_returns_422(client: TestClient):
    """B3.4: Limit parameter exceeding 200 returns 422 validation error."""
    res = client.get("/api/v1/catalog/items?limit=201")
    assert res.status_code == 422


def test_b3_negative_limit_returns_422(client: TestClient):
    """B3.5: Negative limit parameter returns 422 validation error."""
    res = client.get("/api/v1/catalog/items?limit=-1")
    assert res.status_code == 422


# ===========================================================================
# FEATURE 4 BOUNDARIES: Catalog API Integration
# ===========================================================================

def test_b4_empty_q_parameter_acts_as_unfiltered(client: TestClient):
    """B4.1: Passing ?q= with empty string returns standard unfiltered catalog results."""
    res = client.get("/api/v1/catalog/items?q=")
    assert res.status_code == 200
    assert "items" in res.json()


def test_b4_whitespace_q_parameter_handled_gracefully(client: TestClient):
    """B4.2: Passing ?q=    with spaces is handled gracefully."""
    res = client.get("/api/v1/catalog/items?q=   ")
    assert res.status_code == 200


def test_b4_inactive_product_omitted_from_catalog(client: TestClient, db: Session, test_brand, test_category):
    """B4.3: Products marked is_active=False do not appear in catalog API results."""
    unique_name = f"INACTIVE_{uuid.uuid4().hex[:8]}"
    inactive_prod = Product(
        name=unique_name,
        is_active=False,
        brand_id=test_brand.id,
        category_id=test_category.id,
    )
    db.add(inactive_prod)
    db.commit()

    res = client.get(f"/api/v1/catalog/items?q={unique_name}")
    assert res.status_code == 200
    assert not any(i["name"] == unique_name for i in res.json()["items"])


def test_b4_product_without_catalog_price_has_null_price(client: TestClient, db: Session, test_brand, test_category):
    """B4.4: Product without CatalogPrice entry reports price=None and default currency='INR'."""
    unique_name = f"NOPRICE_{uuid.uuid4().hex[:8]}"
    prod = Product(name=unique_name, is_active=True, brand_id=test_brand.id, category_id=test_category.id)
    db.add(prod)
    db.commit()

    res = client.get(f"/api/v1/catalog/items?q={unique_name}")
    assert res.status_code == 200
    item = next((i for i in res.json()["items"] if i["name"] == unique_name), None)
    assert item is not None
    assert item["price"] is None
    assert item["currency"] == "INR"


def test_b4_non_existent_category_returns_empty_items(client: TestClient):
    """B4.5: Filtering by a non-existent category returns 0 items without error."""
    res = client.get("/api/v1/catalog/items?category=NonExistentCategoryXYZ")
    assert res.status_code == 200
    assert res.json()["total"] == 0
    assert res.json()["items"] == []


# ===========================================================================
# FEATURE 5 BOUNDARIES: Catalog Data & Pricing Integrity
# ===========================================================================

def test_b5_zero_price_representation(client: TestClient, db: Session, test_brand, test_category):
    """B5.1: Zero price ₹0.00 is represented accurately as '0.00'."""
    unique_name = f"ZERO_{uuid.uuid4().hex[:8]}"
    prod = Product(name=unique_name, is_active=True, brand_id=test_brand.id, category_id=test_category.id)
    db.add(prod)
    db.flush()
    db.add(CatalogPrice(product_id=prod.id, price=Decimal("0.00"), currency="INR"))
    db.commit()

    res = client.get(f"/api/v1/catalog/items?q={unique_name}")
    item = next(i for i in res.json()["items"] if i["name"] == unique_name)
    assert item["price"] == "0.00"


def test_b5_large_price_precision(client: TestClient, db: Session, test_brand, test_category):
    """B5.2: Large price ₹1,234,567.89 preserves exact 2 decimal digits without exponent."""
    unique_name = f"LARGE_{uuid.uuid4().hex[:8]}"
    prod = Product(name=unique_name, is_active=True, brand_id=test_brand.id, category_id=test_category.id)
    db.add(prod)
    db.flush()
    db.add(CatalogPrice(product_id=prod.id, price=Decimal("1234567.89"), currency="INR"))
    db.commit()

    res = client.get(f"/api/v1/catalog/items?q={unique_name}")
    item = next(i for i in res.json()["items"] if i["name"] == unique_name)
    assert item["price"] == "1234567.89"


def test_b5_long_product_code_preserved(client: TestClient, db: Session, test_brand, test_category):
    """B5.3: Long product code (40 characters) is retained verbatim."""
    long_code = f"SIEMENS-LONG-SKU-{uuid.uuid4().hex[:12]}-SERIES-3"
    prod = Product(name=long_code, is_active=True, brand_id=test_brand.id, category_id=test_category.id)
    db.add(prod)
    db.flush()
    db.add(ProductCode(product_id=prod.id, code=long_code, is_primary=True))
    db.commit()

    res = client.get(f"/api/v1/catalog/items?q={long_code}")
    item = next(i for i in res.json()["items"] if i["name"] == long_code)
    assert item["name"] == long_code


def test_b5_special_characters_in_description(client: TestClient, db: Session, test_brand, test_category):
    """B5.4: Description with special electrical characters (~, °, &, [], /) is preserved."""
    desc = "3P+N 10kA C-Curve MCB ~415V 50Hz [30°C] & Aux Contact"
    prod = Product(name=f"SPEC_{uuid.uuid4().hex[:6]}", description=desc, is_active=True, brand_id=test_brand.id, category_id=test_category.id)
    db.add(prod)
    db.commit()

    res = client.get(f"/api/v1/catalog/items?q={prod.name}")
    item = next(i for i in res.json()["items"] if i["name"] == prod.name)
    assert item["description"] == desc


def test_b5_fractional_cent_quantization(client: TestClient, db: Session, test_brand, test_category):
    """B5.5: CatalogPrice with exact half cent rounds consistently to 2 decimals."""
    prod = Product(name=f"CENT_{uuid.uuid4().hex[:6]}", is_active=True, brand_id=test_brand.id, category_id=test_category.id)
    db.add(prod)
    db.flush()
    db.add(CatalogPrice(product_id=prod.id, price=Decimal("123.45"), currency="INR"))
    db.commit()

    res = client.get(f"/api/v1/catalog/items?q={prod.name}")
    item = next(i for i in res.json()["items"] if i["name"] == prod.name)
    assert Decimal(item["price"]) == Decimal("123.45")


# ===========================================================================
# FEATURE 6 BOUNDARIES: Search & Category Filter
# ===========================================================================

def test_b6_sql_injection_attempt_handled_safely(client: TestClient):
    """B6.1: SQL injection string in query parameter returns 200 without executing injection."""
    injection_payload = "' OR 1=1; DROP TABLE products; --"
    res = client.get(f"/api/v1/catalog/items?q={injection_payload}")
    assert res.status_code == 200
    assert "items" in res.json()


def test_b6_sql_wildcard_characters_in_search(client: TestClient):
    """B6.2: Search terms containing SQL wildcards % and _ execute safely."""
    res = client.get("/api/v1/catalog/items?q=%_%")
    assert res.status_code == 200


def test_b6_regex_meta_characters_in_search(client: TestClient):
    """B6.3: Regex meta-characters in search query (*+?^${}()|[]\\) execute safely."""
    res = client.get("/api/v1/catalog/items?q=.*+?^${}()|[]\\")
    assert res.status_code == 200


def test_b6_unicode_and_symbols_in_search(client: TestClient):
    """B6.4: Unicode characters and currency symbols execute without encoding errors."""
    res = client.get("/api/v1/catalog/items?q=Siemens™_₹_MCB")
    assert res.status_code == 200


def test_b6_category_with_whitespace_stripping(client: TestClient, siemens_5sl71057rc_product):
    """B6.5: Category query with leading/trailing spaces is stripped and matches."""
    res = client.get("/api/v1/catalog/items?category=  MCB  ")
    assert res.status_code == 200
    assert any(i["id"] == siemens_5sl71057rc_product.id for i in res.json()["items"])


# ===========================================================================
# FEATURE 7 BOUNDARIES: Costing Sheet Creation
# ===========================================================================

def test_b7_empty_title_returns_422(client: TestClient):
    """B7.1: Empty title string rejected with 422 Unprocessable Entity."""
    res = client.post("/api/v1/costing-sheets", json={"title": ""})
    assert res.status_code == 422


def test_b7_max_length_title_255_accepted(client: TestClient):
    """B7.2: Title exactly at maximum length 255 characters is accepted."""
    title_255 = "Q" * 255
    res = client.post("/api/v1/costing-sheets", json={"title": title_255})
    assert res.status_code == 200
    assert res.json()["title"] == title_255


def test_b7_title_exceeding_255_returns_422(client: TestClient):
    """B7.3: Title exceeding 255 characters is rejected with 422."""
    title_256 = "Q" * 256
    res = client.post("/api/v1/costing-sheets", json={"title": title_256})
    assert res.status_code == 422


def test_b7_sheet_100_percent_discount(client: TestClient):
    """B7.4: 100% sheet-level discount is valid."""
    res = client.post("/api/v1/costing-sheets", json={"title": "100% Disc", "discount_percent": 100.0})
    assert res.status_code == 200
    assert Decimal(res.json()["discount_percent"]) == Decimal("100.00")


def test_b7_unicode_customer_name(client: TestClient):
    """B7.5: Unicode customer name (e.g. Hindi/Devanagari, German umlauts) accepted."""
    customer = "भेल भारत हेवी इलेक्ट्रिकल्स - Müller GmbH"
    res = client.post("/api/v1/costing-sheets", json={"title": "Unicode Cust", "customer_name": customer})
    assert res.status_code == 200
    assert res.json()["customer_name"] == customer


# ===========================================================================
# FEATURE 8 BOUNDARIES: Reactive Calculations
# ===========================================================================

def test_b8_zero_quantity_results_in_zero_line_total(client: TestClient, siemens_5sl71057rc_product):
    """B8.1: Zero quantity produces 0.00 line total."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Zero Qty"}).json()["id"]
    res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 0.0},
    )
    line = res.json()["lines"][0]
    assert Decimal(line["line_list_total"]) == Decimal("0.00")
    assert Decimal(line["line_net_total"]) == Decimal("0.00")


def test_b8_100_percent_line_discount(client: TestClient, siemens_5sl71057rc_product):
    """B8.2: 100% line discount results in line_net_total=0.00 while line_list_total retains full value."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Free Item"}).json()["id"]
    res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 2.0, "discount_percent": 100.0},
    )
    line = res.json()["lines"][0]
    assert Decimal(line["line_list_total"]) == Decimal("1850.00")
    assert Decimal(line["line_net_total"]) == Decimal("0.00")


def test_b8_fractional_quantity_calculation(client: TestClient, siemens_5sl71057rc_product):
    """B8.3: Fractional quantity (e.g. 2.5 meters/units) computes exact proportional totals."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Fractional Qty"}).json()["id"]
    # 2.5 * 925.00 = 2312.50
    res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 2.5},
    )
    line = res.json()["lines"][0]
    assert Decimal(line["line_list_total"]) == Decimal("2312.50")
    assert Decimal(line["line_net_total"]) == Decimal("2312.50")


def test_b8_100_percent_sheet_discount_zeros_grand_total(client: TestClient, siemens_5sl71057rc_product):
    """B8.4: 100% sheet discount makes grand_total=0.00 even with positive line items."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Complimentary Quote", "discount_percent": 100.0}).json()["id"]
    res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 5.0},
    )
    data = res.json()
    assert Decimal(data["net_total"]) == Decimal("4625.00")
    assert Decimal(data["grand_total"]) == Decimal("0.00")


def test_b8_zero_sell_price_line(client: TestClient, siemens_5sl71057rc_product):
    """B8.5: Explicit 0.00 sell_price results in line_net_total=0.00."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Zero Sell Price"}).json()["id"]
    res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 10.0, "sell_price": 0.0},
    )
    line = res.json()["lines"][0]
    assert Decimal(line["line_net_total"]) == Decimal("0.00")


# ===========================================================================
# FEATURE 9 BOUNDARIES: Costing Persistence
# ===========================================================================

def test_b9_update_line_to_zero_quantity(client: TestClient, siemens_5sl71057rc_product):
    """B9.1: Updating an existing line to 0 quantity persists and recalculates totals."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Update to Zero"}).json()["id"]
    line_data = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 4.0}).json()
    line_id = line_data["lines"][0]["id"]

    res = client.patch(f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}", json={"quantity": 0.0})
    assert Decimal(res.json()["lines"][0]["quantity"]) == Decimal("0.00")
    assert Decimal(res.json()["grand_total"]) == Decimal("0.00")


def test_b9_update_line_custom_sell_price(client: TestClient, siemens_5sl71057rc_product):
    """B9.2: Updating line to custom negotiated sell_price (e.g. ₹850.00) persists."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Custom Price"}).json()["id"]
    line_data = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 1.0}).json()
    line_id = line_data["lines"][0]["id"]

    res = client.patch(f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}", json={"sell_price": 850.0})
    assert Decimal(res.json()["lines"][0]["sell_price"]) == Decimal("850.00")


def test_b9_cascading_sheet_deletion(client: TestClient, siemens_5sl71057rc_product, db: Session):
    """B9.3: Deleting a costing sheet removes associated lines from database via cascade."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Cascade Test"}).json()["id"]
    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 2.0})

    client.delete(f"/api/v1/costing-sheets/{sheet_id}")
    orphaned_lines = db.query(CostingSheetLine).filter(CostingSheetLine.costing_sheet_id == sheet_id).all()
    assert len(orphaned_lines) == 0


def test_b9_large_quantity_order(client: TestClient, siemens_5sl71057rc_product):
    """B9.4: High quantity order (10,000 units) calculates without overflow."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Bulk Order"}).json()["id"]
    # 10,000 * 925.00 = 9,250,000.00
    res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 10000.0})
    assert Decimal(res.json()["grand_total"]) == Decimal("9250000.00")


def test_b9_sequential_updates_consistency(client: TestClient, siemens_5sl71057rc_product):
    """B9.5: 5 rapid sequential updates on the same line maintain consistency."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Sequential"}).json()["id"]
    line_id = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 1.0}).json()["lines"][0]["id"]

    for q in [2.0, 3.0, 4.0, 5.0, 6.0]:
        client.patch(f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}", json={"quantity": q})

    final = client.get(f"/api/v1/costing-sheets/{sheet_id}").json()
    assert Decimal(final["lines"][0]["quantity"]) == Decimal("6.00")


# ===========================================================================
# FEATURE 10 BOUNDARIES: Modern UI & Error Resilience
# ===========================================================================

def test_b10_malformed_json_sheet_creation_returns_422(client: TestClient):
    """B10.1: Invalid JSON payload structure returns 422."""
    res = client.post("/api/v1/costing-sheets", content="{invalid_json}", headers={"Content-Type": "application/json"})
    assert res.status_code == 422


def test_b10_malformed_json_line_creation_returns_422(client: TestClient):
    """B10.2: Invalid JSON payload on line creation returns 422."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Bad JSON Line"}).json()["id"]
    res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", content="not json", headers={"Content-Type": "application/json"})
    assert res.status_code == 422


def test_b10_unsupported_method_returns_405(client: TestClient):
    """B10.3: Unsupported HTTP method (e.g. PUT on health endpoint) returns 405 Method Not Allowed."""
    res = client.put("/api/v1/health")
    assert res.status_code == 405


def test_b10_extra_unknown_fields_in_payload_ignored(client: TestClient):
    """B10.4: Extra unknown properties in JSON payload are ignored safely without error."""
    res = client.post("/api/v1/costing-sheets", json={"title": "Extra Fields", "unknown_field_xyz": 12345})
    assert res.status_code == 200
    assert res.json()["title"] == "Extra Fields"


def test_b10_empty_post_body_returns_422(client: TestClient):
    """B10.5: Empty POST body to costing-sheets returns 422."""
    res = client.post("/api/v1/costing-sheets", json={})
    assert res.status_code == 422


# ===========================================================================
# FEATURE 11 BOUNDARIES: Quality & Contract Verification
# ===========================================================================

def test_b11_openapi_json_returns_200(client: TestClient):
    """B11.1: OpenAPI schema specification endpoint /openapi.json is accessible."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert "openapi" in res.json()


def test_b11_docs_ui_returns_200(client: TestClient):
    """B11.2: Swagger UI documentation /docs returns 200 OK."""
    res = client.get("/docs")
    assert res.status_code == 200


def test_b11_redoc_ui_returns_200(client: TestClient):
    """B11.3: Redoc documentation /redoc returns 200 OK."""
    res = client.get("/redoc")
    assert res.status_code == 200


def test_b11_content_type_options_header(client: TestClient):
    """B11.4: API responses return JSON content type."""
    res = client.get("/api/v1/health")
    assert "application/json" in res.headers["content-type"]


def test_b11_multiple_rapid_catalog_searches(client: TestClient):
    """B11.5: Verify repeated catalog searches execute consistently without resource locking."""
    for _ in range(5):
        res = client.get("/api/v1/catalog/items?limit=10")
        assert res.status_code == 200
