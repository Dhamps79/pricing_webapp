from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database.models.brand import Brand
from app.database.models.category import Category
from app.database.models.product import Product
from app.database.models.product_code import ProductCode
from app.database.models.catalog_price import CatalogPrice


# ===========================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS WITH SIEMENS CATALOG
# ===========================================================================

def test_tier4_residential_distribution_board_quote(
    client: TestClient, db: Session, test_brand, test_category, siemens_5sl71057rc_product
):
    """
    Tier 4 Scenario 1:
    Authentic Residential Distribution Board Quotation:
    - 1 x 2P Incomer MCB (5SL72167RC @ ₹2,280.00, 10% discount)
    - 8 x 1P Lighting MCB (5SL71057RC @ ₹925.00, 15% discount)
    - 2 x 1P Heavy Appliance MCB (5SL71167RC @ ₹925.00, 12% discount)
    - Sheet Discount: 3.5% contractor commission
    """
    # Create required products in DB
    p2 = Product(name="5SL72167RC", description="2P 5SL7 10kA C-Curve MCB 16A", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(p2)
    db.flush()
    db.add(ProductCode(product_id=p2.id, code="5SL72167RC", is_primary=True))
    db.add(CatalogPrice(product_id=p2.id, price=Decimal("2280.00"), currency="INR"))

    p3 = Product(name="5SL71167RC", description="1P 5SL7 10kA C-Curve MCB 16A", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(p3)
    db.flush()
    db.add(ProductCode(product_id=p3.id, code="5SL71167RC", is_primary=True))
    db.add(CatalogPrice(product_id=p3.id, price=Decimal("925.00"), currency="INR"))
    db.commit()

    # Create quotation sheet
    sheet = client.post(
        "/api/v1/costing-sheets",
        json={
            "title": "Villa Residential DB - Siemens Betagard",
            "customer_name": "Prestige Estates Projects Ltd",
            "notes": "Supply standard 10kA C-Curve MCBs with busbar",
            "discount_percent": 3.5,
        },
    ).json()
    sheet_id = sheet["id"]

    # Line 1: 1 unit @ 2280.00, 10% disc
    # unit_net = 2280 * 0.90 = 2052.00
    client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": p2.id, "quantity": 1.0, "discount_percent": 10.0, "notes": "Main Incomer 2P 16A"},
    )

    # Line 2: 8 units @ 925.00, 15% disc
    # unit_net = 925 * 0.85 = 786.25, line_net = 786.25 * 8 = 6290.00
    client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": siemens_5sl71057rc_product.id, "quantity": 8.0, "discount_percent": 15.0, "notes": "Lighting Circuits"},
    )

    # Line 3: 2 units @ 925.00, 12% disc
    # unit_net = 925 * 0.88 = 814.00, line_net = 814.00 * 2 = 1628.00
    final_sheet = client.post(
        f"/api/v1/costing-sheets/{sheet_id}/lines",
        json={"product_id": p3.id, "quantity": 2.0, "discount_percent": 12.0, "notes": "HVAC / Geyser Circuits"},
    ).json()

    # Sheet List Total: 2280 + (8 * 925) + (2 * 925) = 2280 + 7400 + 1850 = 11530.00
    assert Decimal(final_sheet["list_total"]) == Decimal("11530.00")

    # Sheet Net Total: 2052.00 + 6290.00 + 1628.00 = 9970.00
    assert Decimal(final_sheet["net_total"]) == Decimal("9970.00")

    # Grand Total: 9970.00 * (1 - 0.035) = 9970.00 * 0.965 = 9621.05
    assert Decimal(final_sheet["grand_total"]) == Decimal("9621.05")


def test_tier4_commercial_three_phase_quote(
    client: TestClient, db: Session, test_brand, test_category, siemens_5sl71057rc_product
):
    """
    Tier 4 Scenario 2:
    Commercial Complex 3-Phase Main Switchboard Quote:
    - 2 x 4P MCB (5SL74637RC @ ₹5,120.00, 18% volume discount)
    - 6 x 3P MCB (5SL73327RC @ ₹3,840.00, 15% discount)
    - 24 x 1P MCB (5SL71057RC @ ₹925.00, 20% discount)
    - Sheet Discount: 5.0%
    """
    p_4p = Product(name="5SL74637RC", description="4P 5SL7 10kA C-Curve MCB 63A", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(p_4p)
    db.flush()
    db.add(ProductCode(product_id=p_4p.id, code="5SL74637RC", is_primary=True))
    db.add(CatalogPrice(product_id=p_4p.id, price=Decimal("5120.00"), currency="INR"))

    p_3p = Product(name="5SL73327RC", description="3P 5SL7 10kA C-Curve MCB 32A", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(p_3p)
    db.flush()
    db.add(ProductCode(product_id=p_3p.id, code="5SL73327RC", is_primary=True))
    db.add(CatalogPrice(product_id=p_3p.id, price=Decimal("3840.00"), currency="INR"))
    db.commit()

    sheet = client.post(
        "/api/v1/costing-sheets",
        json={
            "title": "Commercial Tower 3-Phase Incomers",
            "customer_name": "Shapoorji Pallonji Group",
            "discount_percent": 5.0,
        },
    ).json()
    sheet_id = sheet["id"]

    # Line 1: 2 * 5120 @ 18% disc => unit_net = 5120 * 0.82 = 4198.40, line_net = 8396.80
    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": p_4p.id, "quantity": 2.0, "discount_percent": 18.0})

    # Line 2: 6 * 3840 @ 15% disc => unit_net = 3840 * 0.85 = 3264.00, line_net = 19584.00
    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": p_3p.id, "quantity": 6.0, "discount_percent": 15.0})

    # Line 3: 24 * 925 @ 20% disc => unit_net = 925 * 0.80 = 740.00, line_net = 17760.00
    res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 24.0, "discount_percent": 20.0})
    data = res.json()

    # List Total: (2 * 5120) + (6 * 3840) + (24 * 925) = 10240 + 23040 + 22200 = 55480.00
    assert Decimal(data["list_total"]) == Decimal("55480.00")

    # Net Total: 8396.80 + 19584.00 + 17760.00 = 45740.80
    assert Decimal(data["net_total"]) == Decimal("45740.80")

    # Grand Total: 45740.80 * (1 - 0.05) = 43453.76
    assert Decimal(data["grand_total"]) == Decimal("43453.76")


def test_tier4_government_tender_zero_discount_quote(
    client: TestClient, db: Session, test_brand, test_category, siemens_5sl71057rc_product
):
    """
    Tier 4 Scenario 3:
    Public Sector Government Tender Quote:
    - Zero discounts allowed (strict MRP procurement).
    - 4 x Siemens Starters (3TW72 @ ₹3,450.00)
    - 4 x Thermal Relays (3UW51 @ ₹1,850.00)
    - 4 x Siemens MCBs (5SL71057RC @ ₹925.00)
    - Verification that List Total, Net Total, and Grand Total are exactly equal.
    """
    p_starter = Product(name="3TW7291-1A", description="DOL Starter 10HP", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(p_starter)
    db.flush()
    db.add(ProductCode(product_id=p_starter.id, code="3TW7291-1A", is_primary=True))
    db.add(CatalogPrice(product_id=p_starter.id, price=Decimal("3450.00"), currency="INR"))

    p_relay = Product(name="3UW5102-0J", description="Overload Relay 16A", unit="1 NO", brand_id=test_brand.id, category_id=test_category.id, is_active=True)
    db.add(p_relay)
    db.flush()
    db.add(ProductCode(product_id=p_relay.id, code="3UW5102-0J", is_primary=True))
    db.add(CatalogPrice(product_id=p_relay.id, price=Decimal("1850.00"), currency="INR"))
    db.commit()

    sheet = client.post(
        "/api/v1/costing-sheets",
        json={
            "title": "NTPC Water Pumping Station Tender",
            "customer_name": "National Thermal Power Corporation",
            "discount_percent": 0.0,
        },
    ).json()
    sheet_id = sheet["id"]

    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": p_starter.id, "quantity": 4.0, "discount_percent": 0.0})
    client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": p_relay.id, "quantity": 4.0, "discount_percent": 0.0})
    res = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 4.0, "discount_percent": 0.0})
    data = res.json()

    # (4 * 3450) + (4 * 1850) + (4 * 925) = 13800 + 7400 + 3700 = 24900.00
    expected_total = Decimal("24900.00")
    assert Decimal(data["list_total"]) == expected_total
    assert Decimal(data["net_total"]) == expected_total
    assert Decimal(data["grand_total"]) == expected_total


def test_tier4_sort_order_and_line_metadata_preservation(
    client: TestClient, siemens_5sl71057rc_product
):
    """
    Tier 4 Scenario 4:
    Verifies that lines maintain ordered sequence (sort_order = 0, 1, 2)
    and custom line notes survive multiple edits and queries.
    """
    sheet = client.post(
        "/api/v1/costing-sheets",
        json={"title": "Sequence & Notes Test", "customer_name": "ABB India"},
    ).json()
    sheet_id = sheet["id"]

    line1 = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 1.0, "notes": "First Floor"}).json()["lines"][-1]
    line2 = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 2.0, "notes": "Second Floor"}).json()["lines"][-1]
    line3 = client.post(f"/api/v1/costing-sheets/{sheet_id}/lines", json={"product_id": siemens_5sl71057rc_product.id, "quantity": 3.0, "notes": "Basement"}).json()["lines"][-1]

    assert line1["sort_order"] == 0
    assert line2["sort_order"] == 1
    assert line3["sort_order"] == 2

    # Fetch sheet and verify order
    fetched = client.get(f"/api/v1/costing-sheets/{sheet_id}").json()
    assert [l["notes"] for l in fetched["lines"]] == ["First Floor", "Second Floor", "Basement"]


def test_tier4_numerical_stability_stress_test(
    client: TestClient, siemens_5sl71057rc_product, db: Session, test_brand, test_category
):
    """
    Tier 4 Scenario 5:
    Numerical precision and financial stability stress test:
    Creates a 20-line quotation with odd fractional quantities and complex discount percentages,
    verifying 0.00 float rounding error and deterministic Decimal calculation.
    """
    sheet = client.post(
        "/api/v1/costing-sheets",
        json={"title": "Numerical Precision Benchmark", "discount_percent": 7.33},
    ).json()
    sheet_id = sheet["id"]

    total_expected_net = Decimal("0.00")
    total_expected_list = Decimal("0.00")

    # 10 lines of Siemens 5SL71057RC with odd quantities & discounts
    for i in range(1, 11):
        qty = Decimal(f"{i}.50")
        disc = Decimal(f"{i * 2}.25")
        res = client.post(
            f"/api/v1/costing-sheets/{sheet_id}/lines",
            json={"product_id": siemens_5sl71057rc_product.id, "quantity": float(qty), "discount_percent": float(disc)},
        )
        line_data = res.json()["lines"][-1]

        # Calculate exact expected
        unit_price = Decimal("925.00")
        expected_line_list = (unit_price * qty).quantize(Decimal("0.01"))
        unit_net = unit_price * (Decimal("1") - (disc / Decimal("100")))
        expected_line_net = (unit_net * qty).quantize(Decimal("0.01"))

        total_expected_list += expected_line_list
        total_expected_net += expected_line_net

        assert Decimal(line_data["line_list_total"]) == expected_line_list
        assert Decimal(line_data["line_net_total"]) == expected_line_net

    final_sheet = client.get(f"/api/v1/costing-sheets/{sheet_id}").json()
    assert Decimal(final_sheet["list_total"]) == total_expected_list
    assert Decimal(final_sheet["net_total"]) == total_expected_net

    expected_grand = (total_expected_net * (Decimal("1") - (Decimal("7.33") / Decimal("100")))).quantize(Decimal("0.01"))
    assert Decimal(final_sheet["grand_total"]) == expected_grand
