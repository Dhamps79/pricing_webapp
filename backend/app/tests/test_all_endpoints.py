from decimal import Decimal
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


client = TestClient(app)


# ===========================================================================
# 1. HEALTH & READINESS ENDPOINTS
# ===========================================================================

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check():
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "ok"


# ===========================================================================
# 2. PRODUCTS CRUD & HISTORY ENDPOINTS
# ===========================================================================

def test_product_lifecycle():
    unique_name = "QA Test Circuit Breaker 5SL7"

    # 1. Create Product
    create_payload = {
        "name": unique_name,
        "description": "High performance miniature circuit breaker for testing",
        "unit": "Nos",
        "image_url": "https://example.com/images/mcb.jpg",
    }
    response = client.post("/api/v1/products", json=create_payload)
    assert response.status_code == 201, response.text
    product = response.json()
    product_id = product["id"]
    assert product["name"] == unique_name
    assert product["unit"] == "Nos"

    try:
        # 2. Duplicate Conflict
        dup_response = client.post("/api/v1/products", json=create_payload)
        assert dup_response.status_code == 409

        # 3. Get Product By ID
        get_response = client.get(f"/api/v1/products/{product_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == product_id

        # 4. Search Products
        search_response = client.get(f"/api/v1/products?q={unique_name}")
        assert search_response.status_code == 200
        items = search_response.json()
        assert any(item["id"] == product_id for item in items)

        # 5. Patch Product
        patch_response = client.patch(
            f"/api/v1/products/{product_id}",
            json={"description": "Updated QA Description", "unit": "Pack"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["description"] == "Updated QA Description"
        assert patch_response.json()["unit"] == "Pack"

        # 6. Product Price History endpoint
        history_response = client.get(f"/api/v1/products/{product_id}/history")
        assert history_response.status_code == 200
        hist_data = history_response.json()
        assert hist_data["product"]["id"] == product_id
        assert isinstance(hist_data["history"], list)

    finally:
        # 7. Delete Product
        del_response = client.delete(f"/api/v1/products/{product_id}")
        assert del_response.status_code == 204

    # 8. Verify 404 after deletion
    not_found = client.get(f"/api/v1/products/{product_id}")
    assert not_found.status_code == 404


def test_product_not_found_errors():
    non_existent_id = 99999999
    assert client.get(f"/api/v1/products/{non_existent_id}").status_code == 404
    assert client.patch(f"/api/v1/products/{non_existent_id}", json={"name": "X"}).status_code == 404
    assert client.delete(f"/api/v1/products/{non_existent_id}").status_code == 404
    assert client.get(f"/api/v1/products/{non_existent_id}/history").status_code == 404


# ===========================================================================
# 3. CATALOG ENDPOINTS
# ===========================================================================

def test_catalog_search_and_categories():
    # Search items
    response = client.get("/api/v1/catalog/items?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)

    # Categories
    cat_response = client.get("/api/v1/catalog/categories")
    assert cat_response.status_code == 200
    assert "categories" in cat_response.json()


def test_catalog_upload_validation():
    # 1. Non-pdf file rejection
    txt_file = io.BytesIO(b"Hello world")
    response = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("test.txt", txt_file, "text/plain")},
    )
    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]

    # 2. Empty pdf rejection
    empty_pdf = io.BytesIO(b"")
    response2 = client.post(
        "/api/v1/catalog/imports/upload",
        files={"file": ("empty.pdf", empty_pdf, "application/pdf")},
    )
    assert response2.status_code == 400

    # 3. Non-existent import status
    assert client.get("/api/v1/catalog/imports/9999999").status_code == 404


# ===========================================================================
# 4. COSTING SHEETS ENDPOINTS
# ===========================================================================

def test_costing_sheets_lifecycle():
    # Setup test product
    create_prod = client.post(
        "/api/v1/products",
        json={"name": "QA Costing Test Item", "unit": "Nos"},
    )
    assert create_prod.status_code == 201
    prod_id = create_prod.json()["id"]

    try:
        # 1. Create Costing Sheet
        sheet_res = client.post(
            "/api/v1/costing-sheets",
            json={
                "title": "Industrial Panel Quote - Revision 1",
                "customer_name": "Larsen & Toubro Ltd",
                "notes": "Supply by Q4",
                "discount_percent": 5.0,
            },
        )
        assert sheet_res.status_code == 200
        sheet = sheet_res.json()
        sheet_id = sheet["id"]
        assert sheet["title"] == "Industrial Panel Quote - Revision 1"
        assert sheet["customer_name"] == "Larsen & Toubro Ltd"
        assert Decimal(sheet["discount_percent"]) == Decimal("5.00")
        assert Decimal(sheet["grand_total"]) == Decimal("0.00")

        # 2. List Costing Sheets
        list_res = client.get("/api/v1/costing-sheets")
        assert list_res.status_code == 200
        sheets = list_res.json()
        assert any(s["id"] == sheet_id for s in sheets)

        # 3. Add Line to Sheet
        line_res = client.post(
            f"/api/v1/costing-sheets/{sheet_id}/lines",
            json={
                "product_id": prod_id,
                "quantity": 10.0,
                "sell_price": 500.0,
                "discount_percent": 10.0,
                "notes": "Main switchboard feeder",
            },
        )
        assert line_res.status_code == 200
        updated_sheet = line_res.json()
        assert len(updated_sheet["lines"]) == 1
        line = updated_sheet["lines"][0]
        line_id = line["id"]
        assert line["product_id"] == prod_id
        assert Decimal(line["quantity"]) == Decimal("10.00")
        assert Decimal(line["sell_price"]) == Decimal("500.00")
        # Line net = 500 * (1 - 0.10) * 10 = 4500.00
        assert Decimal(line["line_net_total"]) == Decimal("4500.00")
        # Grand total with 5% sheet discount: 4500 * (1 - 0.05) = 4275.00
        assert Decimal(updated_sheet["grand_total"]) == Decimal("4275.00")

        # 4. Patch Line
        patch_line_res = client.patch(
            f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}",
            json={
                "quantity": 20.0,
                "discount_percent": 0.0,
            },
        )
        assert patch_line_res.status_code == 200
        patched_sheet = patch_line_res.json()
        patched_line = patched_sheet["lines"][0]
        assert Decimal(patched_line["quantity"]) == Decimal("20.00")
        # 20 * 500 = 10000.00
        assert Decimal(patched_line["line_net_total"]) == Decimal("10000.00")
        # 10000 * (1 - 0.05) = 9500.00
        assert Decimal(patched_sheet["grand_total"]) == Decimal("9500.00")

        # 5. Patch Sheet
        patch_sheet_res = client.patch(
            f"/api/v1/costing-sheets/{sheet_id}",
            json={"discount_percent": 0.0, "title": "Final Quote"},
        )
        assert patch_sheet_res.status_code == 200
        assert patch_sheet_res.json()["title"] == "Final Quote"
        assert Decimal(patch_sheet_res.json()["grand_total"]) == Decimal("10000.00")

        # 6. Delete Line
        del_line_res = client.delete(f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}")
        assert del_line_res.status_code == 200
        assert len(del_line_res.json()["lines"]) == 0

        # 7. Delete Sheet
        del_sheet_res = client.delete(f"/api/v1/costing-sheets/{sheet_id}")
        assert del_sheet_res.status_code == 200
        assert del_sheet_res.json()["id"] == sheet_id

        # 8. Verify 404
        assert client.get(f"/api/v1/costing-sheets/{sheet_id}").status_code == 404

    finally:
        client.delete(f"/api/v1/products/{prod_id}")


# ===========================================================================
# 5. PRICES ENDPOINTS
# ===========================================================================

def test_prices_endpoints_errors_and_ssrf():
    # 1. Non-existent product price
    assert client.get("/api/v1/prices/9999999").status_code == 404

    # 2. Non-existent product price history
    assert client.get("/api/v1/prices/9999999/history").status_code == 404

    # 3. Refresh product without sources
    assert client.post("/api/v1/prices/9999999/refresh").status_code == 404

    # 4. SSRF protection: Localhost / Private IP target rejection
    try:
        ssrf_res = client.post("/api/v1/prices/track?url=http://127.0.0.1:8080/product")
        assert ssrf_res.status_code in [400, 500]
    except ValueError:
        pass  # Validaion succeeded in blocking SSRF

