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
# TIER 3: CROSS-FEATURE COMBINATIONS & PAIRWISE WORKFLOWS
# ===========================================================================

def test_tier3_end_to_end_upload_search_quote_persist_reload(
    client: TestClient, siemens_5sl71057rc_product
):
    """
    Tier 3 Workflow 1:
    Full End-to-End User Flow:
    1. Upload PDF catalog
    2. Check import status
    3. Search catalog for target Siemens MCB
    4. Create costing sheet quote
    5. Add catalog item to quote with quantity and discount
    6. Verify reactive Line Net and List Total math
    7. Apply sheet-level discount and verify Grand Total
    8. Persist, reload sheet from backend, and verify state integrity
    """
    # Step 1: Upload catalog PDF
    pdf_bytes = make_valid_pdf_bytes()
    upload_res = client.post(
        "/api/v1/catalog/imports/upload?supplier_name=Siemens",
        files={"file": ("Siemens_Betagard_Pricelist.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 200
    import_id = upload_res.json()["id"]

    # Step 2: Check import status
    status_res = client.get(f"/api/v1/catalog/imports/{import_id}")
    assert status_res.status_code == 200
    assert status_res.json()["supplier_name"] == "Siemens"

    # Step 3: Search catalog for Siemens 5SL71057RC
    catalog_res = client.get("/api/v1/catalog/items?q=5SL71057RC")
    assert catalog_res.status_code == 200
    items = catalog_res.json()["items"]
    assert len(items) >= 1
    mcb_item = next(i for i in items if i["name"] == "5SL71057RC")
    assert mcb_item["price"] == "925.00"

    # Step 4: Create Costing Sheet
    sheet_payload = {
        "title": f"Substation Feeder Quote {uuid.uuid4().hex[:6]}",
        "customer_name": "Larsen & Toubro Ltd",
        "notes": "Supply Siemens Betagard MCBs by end of month",
        "discount_percent": 0.0,
    }
    create_res = client.post("/api/v1/costing-sheets", json=sheet_payload)
    assert create_res.status_code == 200
    sheet_id = create_res.json()["id"]

    # Step 5: Add item to quote with 12 units and 10% line discount
    line_payload = {
        "product_id": mcb_item["id"],
        "quantity": 12.0,
        "discount_percent": 10.0,
        "notes": "Incomer 1P MCB",
    }
    line_res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json=line_payload)
    assert line_res.status_code == 200
    sheet_data = line_res.json()

    # Step 6: Verify reactive mathematical calculations
    line = sheet_data["lines"][0]
    # list_total = 12 * 925.00 = 11100.00
    assert Decimal(line["line_list_total"]) == Decimal("11100.00")
    # unit_net = 925 * (1 - 0.10) = 832.50
    # line_net = 832.50 * 12 = 9990.00
    assert Decimal(line["line_net_total"]) == Decimal("9990.00")
    assert Decimal(sheet_data["net_total"]) == Decimal("9990.00")

    # Step 7: Apply sheet-level discount of 5%
    patch_res = client.patch(
        f"/api/v1/costing-sheets/{sheet_id}",
        json={"discount_percent": 5.0},
    )
    assert patch_res.status_code == 200
    # Grand Total = 9990.00 * (1 - 0.05) = 9490.50
    assert Decimal(patch_res.json()["grand_total"]) == Decimal("9490.50")

    # Step 8: Reload sheet from backend to verify persistence
    reloaded_res = client.get(f"/api/v1/costing-sheets/{sheet_id}")
    assert reloaded_res.status_code == 200
    reloaded = reloaded_res.json()
    assert reloaded["id"] == sheet_id
    assert reloaded["customer_name"] == "Larsen & Toubro Ltd"
    assert Decimal(reloaded["grand_total"]) == Decimal("9490.50")
    assert len(reloaded["lines"]) == 1


def test_tier3_multi_line_mixed_discounts_and_line_mutations(
    client: TestClient, siemens_5sl71057rc_product, db: Session, test_brand, test_category
):
    """
    Tier 3 Workflow 2:
    Pairwise multi-line interactions with mixed discounts:
    1. Create quote
    2. Add Line 1 (Siemens 1P MCB @ 925, 10 units, 15% discount)
    3. Add Line 2 (Siemens 2P MCB @ 2280, 5 units, 0% discount)
    4. Verify composite List Total and Net Total
    5. Update Line 2 to 8% discount and verify reactive change
    6. Delete Line 1 and verify totals reflect only Line 2
    """
    # Setup second product
    prod2 = Product(name="5SL72167RC", description="2P MCB 16A", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(prod2)
    db.flush()
    db.add(ProductCode(product_id=prod2.id, code="5SL72167RC", is_primary=True))
    db.add(CatalogPrice(product_id=prod2.id, price=Decimal("2280.00"), currency="INR"))
    db.commit()

    # 1. Create quote
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Mixed Discount Quote"}).json()["id"]

    # 2. Add Line 1: 10 * 925 @ 15% disc => unit=786.25, line_net=7862.50, line_list=9250.00
    client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 10.0, "discount_percent": 15.0},
    )

    # 3. Add Line 2: 5 * 2280 @ 0% disc => unit=2280.00, line_net=11400.00, line_list=11400.00
    res2 = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": prod2.id, "quantity": 5.0, "discount_percent": 0.0},
    )
    data2 = res2.json()
    assert len(data2["lines"]) == 2

    # 4. Verify composite List Total = 9250 + 11400 = 20650.00
    assert Decimal(data2["list_total"]) == Decimal("20650.00")
    # Net Total = 7862.50 + 11400.00 = 19262.50
    assert Decimal(data2["net_total"]) == Decimal("19262.50")

    # 5. Update Line 2: set discount to 8%
    line2_id = next(l["id"] for l in data2["lines"] if l["product_id"] == prod2.id)
    patch_line_res = client.patch(
        f"/api/v1/costing-sheets/{sheet_id}/lines/{line2_id}",
        json={"discount_percent": 8.0},
    )
    # Line 2 new net: 2280 * 0.92 = 2097.60 * 5 = 10488.00
    # New Net Total: 7862.50 + 10488.00 = 18350.50
    assert Decimal(patch_line_res.json()["net_total"]) == Decimal("18350.50")

    # 6. Delete Line 1
    line1_id = next(l["id"] for l in data2["lines"] if l["product_id"] == siemens_5sl71057rc_product.id)
    del_res = client.delete(f"/api/v1/costing-sheets/{sheet_id}/lines/{line1_id}")
    del_data = del_res.json()
    assert len(del_data["lines"]) == 1
    # Only Line 2 remains: Net Total = 10488.00, List Total = 11400.00
    assert Decimal(del_data["net_total"]) == Decimal("10488.00")
    assert Decimal(del_data["list_total"]) == Decimal("11400.00")


def test_tier3_multi_quote_isolation(client: TestClient, siemens_5sl71057rc_product):
    """
    Tier 3 Workflow 3:
    Cross-quote isolation:
    Verify that modifying Sheet A has zero effect on Sheet B.
    """
    # Create Sheet A
    res_a = client.post("/api/v1/costing-sheets", json={"title": "Client A Quote", "discount_percent": 5.0})
    sheet_a_id = res_a.json()["id"]
    client.post(f"/api/v1/costing-sheets/{sheet_a_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 10.0})

    # Create Sheet B
    res_b = client.post("/api/v1/costing-sheets", json={"title": "Client B Quote", "discount_percent": 12.0})
    sheet_b_id = res_b.json()["id"]
    client.post(f"/api/v1/costing-sheets/{sheet_b_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 2.0})

    # Record Sheet A state
    state_a_before = client.get(f"/api/v1/costing-sheets/{sheet_a_id}").json()

    # Modify Sheet B heavily
    client.patch(f"/api/v1/costing-sheets/{sheet_b_id}", json={"discount_percent": 25.0, "title": "B Rev 2"})

    # Verify Sheet A state remains unchanged
    state_a_after = client.get(f"/api/v1/costing-sheets/{sheet_a_id}").json()
    assert state_a_before["title"] == state_a_after["title"]
    assert state_a_before["discount_percent"] == state_a_after["discount_percent"]
    assert state_a_before["grand_total"] == state_a_after["grand_total"]


def test_tier3_category_filter_to_quote_line_auto_population(
    client: TestClient, siemens_5sl71057rc_product
):
    """
    Tier 3 Workflow 4:
    Catalog exploration into costing sheet line:
    1. Filter catalog by category 'MCB'
    2. Pick product from category results
    3. Add to costing sheet without providing sell_price
    4. Verify line auto-populates list_price and sell_price from catalog price
    5. Verify line's SKU, name, and unit are automatically populated
    """
    # Step 1: Filter by category
    cat_res = client.get("/api/v1/catalog/items?category=MCB")
    assert cat_res.status_code == 200
    items = cat_res.json()["items"]
    target_item = next(i for i in items if i["id"] == siemens_5sl71057rc_product.id)

    # Step 2: Create costing sheet
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Auto-populate Test"}).json()["id"]

    # Step 3: Add product without specifying sell_price
    res = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": target_item["id"], "quantity": 3.0},
    )
    assert res.status_code == 200
    line = res.json()["lines"][0]

    # Step 4: Verify auto-population of SKU, unit, and prices
    assert line["product_id"] == target_item["id"]
    assert line["sku"] == "5SL71057RC"
    assert line["unit"] == "1 NO"
    assert Decimal(line["list_price"]) == Decimal("925.00")
    assert Decimal(line["sell_price"]) == Decimal("925.00")


def test_tier3_quote_lifecycle_with_customer_negotiation(
    client: TestClient, siemens_5sl71057rc_product
):
    """
    Tier 3 Workflow 5:
    Realistic negotiation lifecycle:
    Draft quote -> Customer requests volume discount -> Update quantities and discounts -> Persist final agreement
    """
    # 1. Draft
    sheet = client.post(
        "/api/v1/costing-sheets",
        json={"title": "Project Alpha - Draft", "customer_name": "Bharat Heavy Electricals"},
    ).json()
    sheet_id = sheet["id"]

    # Add 20 units @ 925
    line = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 20.0},
    ).json()["lines"][0]
    line_id = line["id"]

    # Initial net = 20 * 925 = 18500.00
    assert Decimal(line["line_net_total"]) == Decimal("18500.00")

    # 2. Customer negotiation: increase quantity to 50, provide 12% line discount
    updated_sheet = client.patch(
        f"/api/v1/costing-sheets/{sheet_id}/lines/{line_id}",
        json={"quantity": 50.0, "discount_percent": 12.0, "notes": "Approved volume concession"},
    ).json()
    # 50 * 925 * 0.88 = 40700.00
    assert Decimal(updated_sheet["lines"][0]["line_net_total"]) == Decimal("40700.00")

    # 3. Finalize sheet discount 2.5% and rename title to Final
    final_sheet = client.patch(
        f"/api/v1/costing-sheets/{sheet_id}",
        json={"title": "Project Alpha - Final Agreed", "discount_percent": 2.5},
    ).json()
    # Grand Total: 40700.00 * (1 - 0.025) = 39682.50
    assert Decimal(final_sheet["grand_total"]) == Decimal("39682.50")
    assert final_sheet["title"] == "Project Alpha - Final Agreed"


def test_tier3_search_pagination_add_to_quote_loop(
    client: TestClient, siemens_5sl71057rc_product, db: Session, test_brand, test_category
):
    """
    Tier 3 Workflow 6:
    Iterative catalog pagination exploration and adding multiple products into quote.
    """
    # Create extra catalog products
    for idx in range(3):
        p = Product(name=f"LOOP_MCB_{idx}_{uuid.uuid4().hex[:4]}", is_active=True, brand_id=test_brand.id, category_id=test_category.id)
        db.add(p)
        db.flush()
        db.add(ProductCode(product_id=p.id, code=p.name, is_primary=True))
        db.add(CatalogPrice(product_id=p.id, price=Decimal(f"{(idx+1)*500}.00"), currency="INR"))
    db.commit()

    # Create sheet
    sheet_id = client.post("/api/v1/costing-sheets", json={"title": "Pagination Addition"}).json()["id"]

    # Traverse catalog items page by page and add each to the sheet
    offset = 0
    added_count = 0
    while added_count < 3:
        page_res = client.get(f"/api/v1/catalog/items?limit=2&offset={offset}").json()
        items = page_res["items"]
        if not items:
            break
        for item in items:
            client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": item["id"], "quantity": 1.0})
            added_count += 1
            if added_count >= 3:
                break
        offset += 2

    # Verify sheet has all 3 lines
    final_sheet = client.get(f"/api/v1/costing-sheets/{sheet_id}").json()
    assert len(final_sheet["lines"]) == 3
    assert Decimal(final_sheet["grand_total"]) > Decimal("0.00")
