# Verification Baseline & Regression Safety Plan — Milestone 1 Part 3

**Author**: `teamwork_preview_explorer_m1_3`  
**Date**: 2026-09-08  
**Scope**: Milestone 1 (Catalog Payload Enrichment & TypeScript Build Verification)  
**Target Directories**: `backend/app/tests/`, `frontend/src/`  

---

## 1. Executive Summary

This document establishes the verification baseline, regression safety analysis, test assertions, and exact execution commands for Milestone 1.

Milestone 1 introduces:
1. **Backend Catalog Payload Enrichment**:
   Enriches `catalog_item_payload` (`backend/app/services/catalog_import_service.py`) and `GET /api/v1/catalog/items` (`backend/app/api/v1/catalog.py`) with four new fields:
   - `product_code`: string | null (canonical manufacturer code from primary `ProductCode` or first code)
   - `brand`: string | null (brand name from linked `Brand`)
   - `category`: string | null (category name from linked `Category`)
   - `attributes`: dict (key-value mapping of `ProductAttribute` records, e.g. `{"module_width": "1 MW"}`)
2. **Frontend Type System & Build Pipeline**:
   Adds formal TypeScript definitions for catalog items (`frontend/src/types/catalog.ts`), adds a test script to `frontend/package.json` (`"test": "vitest run"`), and ensures `npm run build` (`tsc -b && vite build`) and `npx vitest run` pass cleanly.

**Core Safety Finding**:
Existing tests in `backend/app/tests/` contain **zero brittle assertions** on the catalog item dictionary keys. Adding the four new fields is **100% backward compatible** and breaks no existing assertions.

---

## 2. Existing Test Suite Inventory

A thorough audit of `backend/app/tests/` and `frontend/` reveals the following test files:

### 2.1 Backend Tests (`backend/app/tests/`)

| File | Line Count | Test Functions | Scope & Coverage | Catalog / Payload Dependency |
|------|------------|----------------|------------------|------------------------------|
| `test_all_endpoints.py` | 270 | 8 | Health, readiness, products CRUD, product history, catalog items, categories, catalog upload validation, costing sheets lifecycle & calculations, prices SSRF | **Lines 107–120** tests `GET /api/v1/catalog/items` and `/categories` |
| `test_siemens_parser.py` | 21 | 3 | Regex tests for `is_siemens_reference()` | None (isolated unit tests) |
| `test_health.py` | 18 | 1 | `GET /api/v1/health` status check | None (isolated endpoint test) |
| `test_products_api.py` | 10 | 1 | Verifies `/api/v1/products` exists in OpenAPI schema paths | None (isolated OpenAPI check) |
| `test_products.py` | 1 | 0 | Empty file (0 bytes) | None |
| `test_categories.py` | 1 | 0 | Empty file (0 bytes) | None |
| `test_brand.py` | 1 | 0 | Empty file (0 bytes) | None |

### 2.2 Frontend Tests (`frontend/`)

| File | Line Count | Test Functions | Scope & Coverage |
|------|------------|----------------|------------------|
| `src/utils/productMapper.test.ts` | 31 | 1 | Tests `productToRow()` mapping legacy `Product` to `ProductRow` with price trends |

---

## 3. Detailed Inspection of Existing Catalog Tests

In `backend/app/tests/test_all_endpoints.py`, Section 3 (lines 104–142):

```python
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
```

### Analysis of Assertions:
1. `response.status_code == 200`: Status code remains 200.
2. `"total" in data`: Response top-level dictionary still contains `"total"`.
3. `"items" in data`: Response top-level dictionary still contains `"items"`.
4. `isinstance(data["items"], list)`: `"items"` remains a list of item dictionaries.
5. In `test_catalog_upload_validation()`: Validates input file validation and 404 handling. Does not inspect item payloads.

**Conclusion**: No assertion compares `data["items"][0]` against an exact schema, counts key lengths, or asserts that only 9 keys exist. All 9 preexisting keys (`id`, `name`, `description`, `unit`, `image_url`, `brand_id`, `category_id`, `price`, `currency`) remain present with identical types.

---

## 4. Regression Risks & Mitigation Matrix

| Risk | Cause | Impact | Mitigation Strategy |
|------|-------|--------|---------------------|
| **N+1 Query Explosion** | Accessing `product.codes`, `product.brand`, `product.category`, `product.attributes` during serialization | When fetching 40 items, up to 160 extra SQL queries are issued. For 200 items, up to 800 extra queries. | In `backend/app/api/v1/catalog.py`, add `.options(selectinload(Product.codes), selectinload(Product.category), selectinload(Product.brand), selectinload(Product.attributes))` to the items query statement. |
| **`AttributeError` on Detached/Mocked Products** | `catalog_item_payload` called with a detached ORM instance or mock object missing relationship attributes | Unhandled exception during serialization | Use safe attribute access: `getattr(item, "brand", None)`, `getattr(item, "category", None)`, `getattr(item, "codes", None) or []`, `getattr(item, "attributes", None) or []`. |
| **`None` Category or Brand** | Unassigned category or brand (`brand_id=None`, `category_id=None`) | Potential `NoneType` attribute access | Safely navigate: `item.brand.name if getattr(item, "brand", None) else None`. |
| **Missing Product Code** | Product without `ProductCode` records | Unhandled index out of range if using `codes[0]` directly | Fallback safely: `next((c.code for c in codes if getattr(c, "is_primary", False)), codes[0].code if codes else None)`. |
| **TypeScript Type Mismatch** | Frontend types expecting `Product` (scraping model) instead of `CatalogItem` | Compilation error during `tsc -b` | Formulate clean `CatalogItem` interface in `frontend/src/types/catalog.ts` with all 13 keys matching the contract in `PROJECT.md`. |

---

## 5. Formulated Unit & Integration Test Assertions

### 5.1 Backend Unit Tests for `catalog_item_payload`

We recommend creating `backend/app/tests/test_catalog_payload.py` (or augmenting `test_all_endpoints.py`):

```python
"""
Unit and integration tests for catalog payload enrichment (Milestone 1).
"""
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.catalog_import_service import catalog_item_payload

client = TestClient(app)


class TestCatalogItemPayloadUnit:
    """Isolated unit tests for catalog_item_payload function."""

    def test_catalog_item_payload_none(self):
        assert catalog_item_payload(None) is None

    def test_catalog_item_payload_complete(self):
        """Verify all 13 fields when product has all relationships populated."""
        mock_product = MagicMock()
        mock_product.id = 101
        mock_product.name = "5SL71057RC"
        mock_product.description = "1P 5SL7 10kA C-Curve MCB 0.5A"
        mock_product.unit = "1 NO"
        mock_product.image_url = "https://example.com/img.jpg"
        mock_product.brand_id = 1
        mock_product.category_id = 2

        # Brand
        mock_brand = MagicMock()
        mock_brand.name = "Siemens"
        mock_product.brand = mock_brand

        # Category
        mock_category = MagicMock()
        mock_category.name = "MCB"
        mock_product.category = mock_category

        # Codes (primary code)
        code1 = MagicMock(code="SEC-001", is_primary=False)
        code2 = MagicMock(code="5SL71057RC", is_primary=True)
        mock_product.codes = [code1, code2]

        # Attributes
        attr1 = MagicMock(attribute_name="module_width", attribute_value="1 MW")
        attr2 = MagicMock(attribute_name="rated_current", attribute_value="0.5A")
        mock_product.attributes = [attr1, attr2]

        payload = catalog_item_payload(
            mock_product,
            price=Decimal("925.00"),
            currency="INR",
        )

        assert payload is not None
        # Verify all 13 fields
        assert payload["id"] == 101
        assert payload["product_code"] == "5SL71057RC"
        assert payload["name"] == "5SL71057RC"
        assert payload["description"] == "1P 5SL7 10kA C-Curve MCB 0.5A"
        assert payload["unit"] == "1 NO"
        assert payload["image_url"] == "https://example.com/img.jpg"
        assert payload["brand_id"] == 1
        assert payload["brand"] == "Siemens"
        assert payload["category_id"] == 2
        assert payload["category"] == "MCB"
        assert payload["price"] == "925.00"
        assert payload["currency"] == "INR"
        assert payload["attributes"] == {
            "module_width": "1 MW",
            "rated_current": "0.5A",
        }

    def test_catalog_item_payload_null_safe(self):
        """Verify fallback behavior when relations are None or empty."""
        mock_product = MagicMock()
        mock_product.id = 102
        mock_product.name = "Generic Item"
        mock_product.description = None
        mock_product.unit = None
        mock_product.image_url = None
        mock_product.brand_id = None
        mock_product.brand = None
        mock_product.category_id = None
        mock_product.category = None
        mock_product.codes = []
        mock_product.attributes = []

        payload = catalog_item_payload(mock_product, price=None, currency="INR")

        assert payload is not None
        assert payload["id"] == 102
        assert payload["product_code"] is None
        assert payload["brand"] is None
        assert payload["category"] is None
        assert payload["attributes"] == {}
        assert payload["price"] is None
        assert payload["currency"] == "INR"

    def test_catalog_item_payload_fallback_to_first_code_if_no_primary(self):
        """When no code is marked is_primary, fall back to first code in list."""
        mock_product = MagicMock()
        mock_product.id = 103
        mock_product.name = "Item Without Primary Code"
        mock_product.brand = None
        mock_product.category = None
        mock_product.attributes = []

        code1 = MagicMock(code="FALLBACK-CODE-1", is_primary=False)
        code2 = MagicMock(code="FALLBACK-CODE-2", is_primary=False)
        mock_product.codes = [code1, code2]

        payload = catalog_item_payload(mock_product)
        assert payload["product_code"] == "FALLBACK-CODE-1"


class TestCatalogEndpointIntegration:
    """Integration assertions against GET /api/v1/catalog/items."""

    def test_catalog_items_response_structure(self):
        response = client.get("/api/v1/catalog/items?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

        # If database contains catalog items, verify contract on each item
        expected_keys = {
            "id",
            "product_code",
            "name",
            "description",
            "unit",
            "image_url",
            "brand_id",
            "brand",
            "category_id",
            "category",
            "price",
            "currency",
            "attributes",
        }
        for item in data["items"]:
            assert expected_keys.issubset(item.keys())
            assert isinstance(item["attributes"], dict)
            assert item["currency"] == "INR" or item["currency"] is not None
```

### 5.2 Frontend TypeScript Contract (`frontend/src/types/catalog.ts`)

```typescript
export interface CatalogItem {
  id: number;
  product_code: string | null;
  name: string;
  description: string | null;
  unit: string | null;
  image_url: string | null;
  brand_id: number | null;
  brand: string | null;
  category_id: number | null;
  category: string | null;
  price: string | null;
  currency: string;
  attributes: Record<string, string>;
}

export interface CatalogItemsResponse {
  total: number;
  items: CatalogItem[];
}

export interface CatalogCategoriesResponse {
  categories: string[];
}

export interface CatalogImportResponse {
  id: number;
  file_name: string;
  supplier_name: string | null;
  status: string;
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  created_at: string;
  completed_at: string | null;
}
```

### 5.3 Frontend `package.json` Test Script

In `frontend/package.json`, under `"scripts"`:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "oxlint",
    "preview": "vite preview",
    "test": "vitest run"
  }
}
```

---

## 6. Exact Verification Commands and Expected Passing Outcomes

### 6.1 Backend Verification

1. **Full Backend Test Suite**:
   ```bash
   cd backend
   pytest -q
   ```
   **Expected Outcome**:
   - Discovers `test_all_endpoints.py`, `test_siemens_parser.py`, `test_health.py`, `test_products_api.py`.
   - Exit code: `0`.
   - Output contains: `X passed in Ys` (100% pass rate).

2. **Verbose Endpoint Test Run**:
   ```bash
   cd backend
   pytest -v app/tests/test_all_endpoints.py
   ```
   **Expected Outcome**:
   - `test_health_check` PASSED
   - `test_readiness_check` PASSED
   - `test_product_lifecycle` PASSED
   - `test_product_not_found_errors` PASSED
   - `test_catalog_search_and_categories` PASSED
   - `test_catalog_upload_validation` PASSED
   - `test_costing_sheets_lifecycle` PASSED
   - `test_prices_endpoints_errors_and_ssrf` PASSED

3. **Catalog Payload Unit Tests**:
   ```bash
   cd backend
   pytest -v app/tests/test_catalog_payload.py
   ```
   **Expected Outcome**:
   - All isolated unit tests for `catalog_item_payload` PASSED.

---

### 6.2 Frontend Verification

1. **TypeScript Compilation and Production Build**:
   ```bash
   cd frontend
   npm run build
   ```
   **Expected Outcome**:
   - Runs `tsc -b && vite build`.
   - `tsc -b` exits with `0` (zero type errors).
   - `vite build` bundles assets into `dist/` directory without syntax or module errors.
   - Overall exit code: `0`.

2. **Automated Unit Tests with Vitest**:
   ```bash
   cd frontend
   npx vitest run
   ```
   (or `npm test`)
   **Expected Outcome**:
   - Executes Vitest on `src/utils/productMapper.test.ts` (and any new test files).
   - Exit code: `0`.
   - 100% test pass rate.

---

## 7. Invalidation Matrix

This plan's conclusions will be invalidated if any of the following occur:
1. An existing backend test explicitly fails when extra keys are present in dictionary responses (tested and confirmed FALSE: no such assertions exist).
2. The database schema does not have the `ProductCode`, `Brand`, `Category`, or `ProductAttribute` tables (verified and confirmed FALSE: all tables exist and have mapped relationships on `Product`).
3. `tsc -b` flags existing type errors in `frontend/src/` unrelated to catalog types (must be verified during frontend build fix).
4. `catalog_item_payload` is called in other unmonitored services (verified by full regex grep: only called in `backend/app/api/v1/catalog.py`).
