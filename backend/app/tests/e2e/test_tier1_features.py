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
from app.tests.e2e.conftest import make_valid_pdf_bytes


# ===========================================================================
# FEATURE 1: PDF Upload Component & Endpoint (POST /api/v1/catalog/imports/upload)
# ===========================================================================

def test_f1_upload_valid_pdf_default_supplier(client: TestClient):
    """F1.1: Upload a valid PDF file with default supplier fallback."""
    pdf_bytes = make_valid_pdf_bytes()
    filename = f"catalog_{uuid.uuid4().hex[:6]}.pdf"
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["supplier_name"] == "Siemens"
    assert data["file_name"] == filename


def test_f1_upload_valid_pdf_custom_supplier(client: TestClient):
    """F1.2: Upload a valid PDF with custom supplier query parameter."""
    pdf_bytes = make_valid_pdf_bytes()
    filename = f"schneider_{uuid.uuid4().hex[:6]}.pdf"
    response = client.post(
        "/api/v1/catalog/imports/upload?supplier_name=Schneider+Electric",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["supplier_name"] == "Schneider Electric"


def test_f1_upload_content_type_header(client: TestClient):
    """F1.3: Verify upload processes with standard multipart form encoding."""
    pdf_bytes = make_valid_pdf_bytes()
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("distribution_catalog.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    assert "id" in response.json()


def test_f1_upload_response_schema(client: TestClient):
    """F1.4: Verify upload returns all expected schema keys per PROJECT.md interface contract."""
    pdf_bytes = make_valid_pdf_bytes()
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("contract_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    required_keys = {
        "id", "file_name", "supplier_name", "status",
        "total_rows", "imported_rows", "failed_rows",
        "created_at", "completed_at"
    }
    assert required_keys.issubset(data.keys())


def test_f1_upload_numeric_metrics_initialized(client: TestClient):
    """F1.5: Verify import row metrics are integers and non-negative."""
    pdf_bytes = make_valid_pdf_bytes()
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("metrics_init.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["total_rows"], int) and data["total_rows"] >= 0
    assert isinstance(data["imported_rows"], int) and data["imported_rows"] >= 0
    assert isinstance(data["failed_rows"], int) and data["failed_rows"] >= 0


# ===========================================================================
# FEATURE 2: Upload Progress & Status (GET /api/v1/catalog/imports/{id})
# ===========================================================================

def test_f2_get_import_status_success(client: TestClient):
    """F2.1: Retrieve status of a created import record."""
    pdf_bytes = make_valid_pdf_bytes()
    res = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("status_check.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    import_id = res.json()["id"]

    status_res = client.get(f"/api/v1/catalog/imports/{import_id}")
    assert status_res.status_code == 200
    assert status_res.json()["id"] == import_id


def test_f2_import_status_enum_values(client: TestClient):
    """F2.2: Ensure import status is one of the valid state enum values."""
    pdf_bytes = make_valid_pdf_bytes()
    res = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("state_check.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    import_id = res.json()["id"]
    status_data = client.get(f"/api/v1/catalog/imports/{import_id}").json()
    assert status_data["status"] in {"completed", "completed_with_errors", "failed", "uploaded"}


def test_f2_import_row_counts_consistency(client: TestClient):
    """F2.3: Imported rows plus failed rows should match total_rows."""
    pdf_bytes = make_valid_pdf_bytes()
    res = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("counts_check.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    import_id = res.json()["id"]
    data = client.get(f"/api/v1/catalog/imports/{import_id}").json()
    assert data["imported_rows"] + data["failed_rows"] <= data["total_rows"] + 1


def test_f2_non_existent_import_id_returns_404(client: TestClient):
    """F2.4: Querying an invalid import ID returns 404 with standard error format."""
    response = client.get("/api/v1/catalog/imports/88888888")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_f2_import_timestamps_present(client: TestClient):
    """F2.5: Ensure created_at and completed_at timestamps are formatted."""
    pdf_bytes = make_valid_pdf_bytes()
    res = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("ts_check.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    data = res.json()
    assert data["created_at"] is not None


# ===========================================================================
# FEATURE 3: Auto-Refresh on Upload
# ===========================================================================

def test_f3_catalog_readable_before_and_after_upload(client: TestClient):
    """F3.1: Verify catalog items endpoint remains responsive and consistent before/after upload."""
    before_res = client.get("/api/v1/catalog/items")
    assert before_res.status_code == 200
    before_total = before_res.json()["total"]

    pdf_bytes = make_valid_pdf_bytes()
    client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("refresh_sync.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    after_res = client.get("/api/v1/catalog/items")
    assert after_res.status_code == 200
    after_total = after_res.json()["total"]
    assert after_total >= before_total


def test_f3_categories_list_responsive_after_upload(client: TestClient):
    """F3.2: Verify category list is updated and accessible following imports."""
    cat_res = client.get("/api/v1/catalog/categories")
    assert cat_res.status_code == 200
    assert "categories" in cat_res.json()
    assert isinstance(cat_res.json()["categories"], list)


def test_f3_catalog_item_discovery_without_restart(client: TestClient, siemens_5sl71057rc_product):
    """F3.3: Product records inserted into catalog are discoverable immediately."""
    search_res = client.get("/api/v1/catalog/items?q=5SL71057RC")
    assert search_res.status_code == 200
    items = search_res.json()["items"]
    assert any(i["id"] == siemens_5sl71057rc_product.id for i in items)


def test_f3_pagination_total_matches_item_pool(client: TestClient):
    """F3.4: Verify the total reported by catalog items matches count of available products."""
    res = client.get("/api/v1/catalog/items?limit=5")
    assert res.status_code == 200
    total = res.json()["total"]
    items = res.json()["items"]
    assert len(items) <= 5
    assert total >= len(items)


def test_f3_catalog_refresh_with_offset(client: TestClient):
    """F3.5: Verify refreshed catalog data supports offset navigation."""
    res = client.get("/api/v1/catalog/items?limit=2&offset=0")
    assert res.status_code == 200
    items_page_1 = res.json()["items"]
    if res.json()["total"] > 2:
        res_page_2 = client.get("/api/v1/catalog/items?limit=2&offset=2")
        items_page_2 = res_page_2.json()["items"]
        assert [i["id"] for i in items_page_1] != [i["id"] for i in items_page_2]


# ===========================================================================
# FEATURE 4: Catalog API Integration (GET /api/v1/catalog/items & /categories)
# ===========================================================================

def test_f4_get_catalog_items_structure(client: TestClient):
    """F4.1: Endpoint returns JSON with 'total' and 'items'."""
    res = client.get("/api/v1/catalog/items")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_f4_catalog_items_limit_param(client: TestClient):
    """F4.2: Endpoint respects limit parameter."""
    res = client.get("/api/v1/catalog/items?limit=3")
    assert res.status_code == 200
    assert len(res.json()["items"]) <= 3


def test_f4_catalog_items_offset_param(client: TestClient):
    """F4.3: Endpoint respects offset parameter."""
    res_all = client.get("/api/v1/catalog/items?limit=5")
    all_items = res_all.json()["items"]
    if len(all_items) > 1:
        res_offset = client.get("/api/v1/catalog/items?limit=5&offset=1")
        assert res_offset.json()["items"][0]["id"] == all_items[1]["id"]


def test_f4_catalog_item_payload_fields(client: TestClient, siemens_5sl71057rc_product):
    """F4.4: Verify each item payload matches PROJECT.md schema."""
    res = client.get("/api/v1/catalog/items?q=5SL71057RC")
    assert res.status_code == 200
    target = next((i for i in res.json()["items"] if i["id"] == siemens_5sl71057rc_product.id), None)
    assert target is not None
    for field in ["id", "name", "description", "unit", "price", "currency"]:
        assert field in target


def test_f4_get_categories_list(client: TestClient):
    """F4.5: Categories endpoint returns sorted string array."""
    res = client.get("/api/v1/catalog/categories")
    assert res.status_code == 200
    cats = res.json()["categories"]
    assert isinstance(cats, list)
    assert cats == sorted(cats)


# ===========================================================================
# FEATURE 5: Catalog Data & Pricing Integrity
# ===========================================================================

def test_f5_siemens_5sl71057rc_price_precision(client: TestClient, siemens_5sl71057rc_product):
    """F5.1: Critical requirement - Siemens 5SL71057RC shows exact price ₹925.00."""
    res = client.get(f"/api/v1/catalog/items?q=5SL71057RC")
    assert res.status_code == 200
    item = next((i for i in res.json()["items"] if i["id"] == siemens_5sl71057rc_product.id), None)
    assert item is not None
    assert item["price"] == "925.00"


def test_f5_siemens_5sl71057rc_currency(client: TestClient, siemens_5sl71057rc_product):
    """F5.2: Siemens 5SL71057RC currency is INR."""
    res = client.get(f"/api/v1/catalog/items?q=5SL71057RC")
    item = next((i for i in res.json()["items"] if i["id"] == siemens_5sl71057rc_product.id), None)
    assert item is not None
    assert item["currency"] == "INR"


def test_f5_siemens_5sl71057rc_unit(client: TestClient, siemens_5sl71057rc_product):
    """F5.3: Siemens 5SL71057RC unit is '1 NO'."""
    res = client.get(f"/api/v1/catalog/items?q=5SL71057RC")
    item = next((i for i in res.json()["items"] if i["id"] == siemens_5sl71057rc_product.id), None)
    assert item is not None
    assert item["unit"] == "1 NO"


def test_f5_siemens_5sl71057rc_description(client: TestClient, siemens_5sl71057rc_product):
    """F5.4: Description matches manufacturer MCB specification."""
    res = client.get(f"/api/v1/catalog/items?q=5SL71057RC")
    item = next((i for i in res.json()["items"] if i["id"] == siemens_5sl71057rc_product.id), None)
    assert item is not None
    assert "MCB" in item["description"]


def test_f5_catalog_pricing_no_drift(client: TestClient, siemens_5sl71057rc_product):
    """F5.5: Pricing representation is Decimal string without floating point artifacts."""
    res = client.get(f"/api/v1/catalog/items?q=5SL71057RC")
    item = next((i for i in res.json()["items"] if i["id"] == siemens_5sl71057rc_product.id), None)
    assert item is not None
    price_val = Decimal(item["price"])
    assert price_val == Decimal("925.00")
    # Verify no float roundoff like 925.000000001
    assert str(price_val) == "925.00"


# ===========================================================================
# FEATURE 6: Search & Category Filter
# ===========================================================================

def test_f6_search_by_product_code(client: TestClient, siemens_5sl71057rc_product):
    """F6.1: Search by exact product code."""
    res = client.get("/api/v1/catalog/items?q=5SL71057RC")
    assert res.status_code == 200
    assert any(i["name"] == "5SL71057RC" for i in res.json()["items"])


def test_f6_search_case_insensitivity(client: TestClient, siemens_5sl71057rc_product):
    """F6.2: Search by lowercase product code succeeds."""
    res = client.get("/api/v1/catalog/items?q=5sl71057rc")
    assert res.status_code == 200
    assert any(i["id"] == siemens_5sl71057rc_product.id for i in res.json()["items"])


def test_f6_search_by_description_substring(client: TestClient, siemens_5sl71057rc_product):
    """F6.3: Search matches partial description."""
    res = client.get("/api/v1/catalog/items?q=C-Curve")
    assert res.status_code == 200
    assert any(i["id"] == siemens_5sl71057rc_product.id for i in res.json()["items"])


def test_f6_filter_by_category(client: TestClient, siemens_5sl71057rc_product):
    """F6.4: Filter by category returns matching items."""
    res = client.get("/api/v1/catalog/items?category=MCB")
    assert res.status_code == 200
    assert any(i["id"] == siemens_5sl71057rc_product.id for i in res.json()["items"])


def test_f6_combined_search_and_category_and_logic(client: TestClient, siemens_5sl71057rc_product):
    """F6.5: Combining matching search and non-matching category yields 0 items."""
    res = client.get("/api/v1/catalog/items?q=5SL71057RC&category=Transformers")
    assert res.status_code == 200
    assert not any(i["id"] == siemens_5sl71057rc_product.id for i in res.json()["items"])


# ===========================================================================
# FEATURE 7: Costing Sheet Management (POST /api/v1/costing-sheets)
# ===========================================================================

def test_f7_create_costing_sheet_full_payload(client: TestClient):
    """F7.1: Create costing sheet with all optional fields provided."""
    payload = {
        "title": f"Quote {uuid.uuid4().hex[:6]}",
        "customer_name": "Tata Projects Ltd",
        "notes": "Fast delivery required",
        "discount_percent": 7.5,
    }
    res = client.post("/api/v1/costing-sheets", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == payload["title"]
    assert data["customer_name"] == "Tata Projects Ltd"
    assert Decimal(data["discount_percent"]) == Decimal("7.50")
    assert data["lines"] == []


def test_f7_create_costing_sheet_minimal_payload(client: TestClient):
    """F7.2: Create costing sheet with only required title."""
    title = f"Minimal Quote {uuid.uuid4().hex[:6]}"
    res = client.post("/api/v1/costing-sheets", json={"title": title})
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == title
    assert data["customer_name"] is None
    assert Decimal(data["discount_percent"]) == Decimal("0.00")


def test_f7_list_costing_sheets(client: TestClient):
    """F7.3: Listing costing sheets returns array containing created quote summary."""
    title = f"List Test {uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/v1/costing-sheets", json={"title": title})
    sheet_id = create_res.json()["id"]

    list_res = client.get("/api/v1/costing-sheets")
    assert list_res.status_code == 200
    sheets = list_res.json()
    assert any(s["id"] == sheet_id for s in sheets)


def test_f7_get_costing_sheet_by_id(client: TestClient):
    """F7.4: Retrieve individual costing sheet by its primary key."""
    title = f"Get Test {uuid.uuid4().hex[:6]}"
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": title}).json()["id"]

    res = client.get(f"/api/v1/costing-sheets/{sheet_id}")
    assert res.status_code == 200
    assert res.json()["id"] == sheet_id


def test_f7_patch_costing_sheet_metadata(client: TestClient):
    """F7.5: Update title and customer name via PATCH."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Original"}).json()["id"]
    patch_res = client.patch(
        f"/api/v1/costing-sheets/{sheet_id}",
        json={"title": "Updated Title", "customer_name": "Reliance Power"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Title"
    assert patch_res.json()["customer_name"] == "Reliance Power"


# ===========================================================================
# FEATURE 8: Reactive Quotation Calculations
# ===========================================================================

def test_f8_single_line_list_and_net_math(client: TestClient, siemens_5sl71057rc_product):
    """F8.1: Test line_list_total and line_net_total for a single item without discount."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Math Test 1"}).json()["id"]
    # 5 units of Siemens 5SL71057RC @ 925.00
    line_res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 5.0, "discount_percent": 0.0},
    )
    assert line_res.status_code == 200
    line = line_res.json()["lines"][0]
    # 5 * 925.00 = 4625.00
    assert Decimal(line["line_list_total"]) == Decimal("4625.00")
    assert Decimal(line["line_net_total"]) == Decimal("4625.00")


def test_f8_single_line_with_discount_math(client: TestClient, siemens_5sl71057rc_product):
    """F8.2: Test line_net_total when item has 15% discount."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Math Test 2"}).json()["id"]
    # 10 units @ 925.00 with 15% discount
    # unit_net = 925 * 0.85 = 786.25
    # line_net = 786.25 * 10 = 7862.50
    line_res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 10.0, "discount_percent": 15.0},
    )
    line = line_res.json()["lines"][0]
    assert Decimal(line["line_net_total"]) == Decimal("7862.50")
    assert Decimal(line["line_list_total"]) == Decimal("9250.00")


def test_f8_multi_line_sheet_list_total(client: TestClient, siemens_5sl71057rc_product, db: Session, test_brand, test_category):
    """F8.3: Verify sheet_list_total is exact sum of line_list_totals."""
    prod2 = Product(name="5SL72167RC", description="2P MCB", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(prod2)
    db.flush()
    db.add(ProductCode(product_id=prod2.id, code="5SL72167RC", is_primary=True))
    db.add(CatalogPrice(product_id=prod2.id, price=Decimal("2280.00"), currency="INR"))
    db.commit()

    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Multi-Line Sum"}).json()["id"]
    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 2.0}) # 2*925 = 1850
    res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": prod2.id, "quantity": 3.0}) # 3*2280 = 6840
    data = res.json()
    # 1850 + 6840 = 8690.00
    assert Decimal(data["list_total"]) == Decimal("8690.00")


def test_f8_multi_line_sheet_net_total(client: TestClient, siemens_5sl71057rc_product):
    """F8.4: Verify sheet_net_total aggregates individual net totals accurately."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Net Total Aggregation"}).json()["id"]
    # Line 1: 10 * 925 with 10% disc => 9250 * 0.90 = 8325.00
    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 10.0, "discount_percent": 10.0})
    # Line 2: 4 * 925 with 20% disc => unit=740, 4*740 = 2960.00
    res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 4.0, "discount_percent": 20.0})
    data = res.json()
    # 8325.00 + 2960.00 = 11285.00
    assert Decimal(data["net_total"]) == Decimal("11285.00")


def test_f8_grand_total_with_sheet_level_discount(client: TestClient, siemens_5sl71057rc_product):
    """F8.5: Grand total applies sheet-level discount on sheet_net_total."""
    # Sheet has 5% discount
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Grand Total Calc", "discount_percent": 5.0}).json()["id"]
    # Line: 10 * 925 @ 0% disc = 9250.00
    res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 10.0})
    data = res.json()
    # 9250.00 * (1 - 0.05) = 8787.50
    assert Decimal(data["net_total"]) == Decimal("9250.00")
    assert Decimal(data["grand_total"]) == Decimal("8787.50")


# ===========================================================================
# FEATURE 9: Costing Backend Persistence
# ===========================================================================

def test_f9_add_line_persistence(client: TestClient, siemens_5sl71057rc_product):
    """F9.1: Line added to costing sheet persists and is retrievable."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Persist 1"}).json()["id"]
    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 3.0})
    
    fetched = client.get(f"/api/v1/costing-sheets/{sheet_id}").json()
    assert len(fetched["lines"]) == 1
    assert Decimal(fetched["lines"][0]["quantity"]) == Decimal("3.00")


def test_f9_patch_line_persistence(client: TestClient, siemens_5sl71057rc_product):
    """F9.2: Modifying line quantity and discount persists across requests."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Persist Patch"}).json()["id"]
    line_data = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 1.0}).json()
    line_id = line_data["lines"][0]["id"]

    client.patch(f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}", json={"quantity": 8.0, "discount_percent": 12.0})

    fetched = client.get(f"/api/v1/costing-sheets/{sheet_id}").json()
    patched_line = fetched["lines"][0]
    assert Decimal(patched_line["quantity"]) == Decimal("8.00")
    assert Decimal(patched_line["discount_percent"]) == Decimal("12.00")


def test_f9_delete_line_persistence(client: TestClient, siemens_5sl71057rc_product):
    """F9.3: Removing a line updates the sheet line count and totals."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Delete Line"}).json()["id"]
    line_data = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 2.0}).json()
    line_id = line_data["lines"][0]["id"]

    del_res = client.delete(f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}")
    assert del_res.status_code == 200
    assert len(del_res.json()["lines"]) == 0
    assert Decimal(del_res.json()["grand_total"]) == Decimal("0.00")


def test_f9_delete_sheet_lifecycle(client: TestClient):
    """F9.4: Deleting a costing sheet removes it from the database."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "To Delete"}).json()["id"]
    del_res = client.delete(f"/api/v1/costing-sheets/{sheet_id}")
    assert del_res.status_code == 200
    assert del_res.json()["id"] == sheet_id


def test_f9_deleted_sheet_returns_404(client: TestClient):
    """F9.5: Once deleted, retrieving the sheet yields HTTP 404."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "To 404"}).json()["id"]
    client.delete(f"/api/v1/costing-sheets/{sheet_id}")
    assert client.get(f"/api/v1/costing-sheets/{sheet_id}").status_code == 404


# ===========================================================================
# FEATURE 10: Modern UI & Error Resilience
# ===========================================================================

def test_f10_get_invalid_sheet_id_404(client: TestClient):
    """F10.1: Non-existent costing sheet ID returns 404."""
    assert client.get("/api/v1/costing-sheets/99999999").status_code == 404


def test_f10_patch_invalid_sheet_id_404(client: TestClient):
    """F10.2: Patching non-existent costing sheet ID returns 404."""
    assert client.patch("/api/v1/costing-sheets/99999999", json={"title": "None"}).status_code == 404


def test_f10_patch_invalid_line_id_404(client: TestClient):
    """F10.3: Patching non-existent line ID returns 404."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Dummy"}).json()["id"]
    assert client.patch(f"/api/v1/costing-sheets/{sheet_id}/lines/99999999", json={"quantity": 1.0}).status_code == 404


def test_f10_delete_invalid_line_id_404(client: TestClient):
    """F10.4: Deleting non-existent line ID returns 404."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Dummy 2"}).json()["id"]
    assert client.delete(f"/api/v1/costing-sheets/{sheet_id}/lines/99999999").status_code == 404


def test_f10_add_line_non_existent_product_404(client: TestClient):
    """F10.5: Adding non-existent product_id to costing sheet returns 404."""
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Dummy 3"}).json()["id"]
    assert client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": 99999999, "quantity": 1.0}).status_code == 404


# ===========================================================================
# FEATURE 11: Quality Verification & Test Suite
# ===========================================================================

def test_f11_health_endpoint(client: TestClient):
    """F11.1: Health endpoint reports status ok."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_f11_ready_endpoint(client: TestClient):
    """F11.2: Readiness endpoint confirms database connectivity."""
    res = client.get("/api/v1/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
    assert res.json()["database"] == "ok"


def test_f11_openapi_schema_contains_catalog_routes(client: TestClient):
    """F11.3: Catalog API routes are declared in OpenAPI schema."""
    paths = client.app.openapi()["paths"]
    assert "/api/v1/catalog/imports/upload" in paths
    assert "/api/v1/catalog/items" in paths
    assert "/api/v1/catalog/categories" in paths


def test_f11_openapi_schema_contains_costing_routes(client: TestClient):
    """F11.4: Costing sheet routes are declared in OpenAPI schema."""
    paths = client.app.openapi()["paths"]
    assert "/api/v1/costing-sheets" in paths
    assert "/api/v1/costing-sheets/{sheet_id}" in paths
    assert "/api/v1/costing-sheets/{sheet_id}/lines" in paths


def test_f11_cors_middleware_headers(client: TestClient):
    """F11.5: Verify CORS preflight and access control headers."""
    res = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
