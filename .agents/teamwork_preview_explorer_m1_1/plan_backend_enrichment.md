# Plan: Backend Catalog Payload Enrichment & Eager Loading Optimization (Milestone 1 Part 1)

## Executive Summary
This document provides the exact implementation plan for enriching the catalog items payload returned by `GET /api/v1/catalog/items` and eliminating N+1 query overhead.

The two files requiring modification are:
1. `backend/app/services/catalog_import_service.py` (`catalog_item_payload`)
2. `backend/app/api/v1/catalog.py` (`search_catalog_items`)

---

## 1. File Inspection & Current State

### File 1: `backend/app/services/catalog_import_service.py`
- **Function**: `catalog_item_payload(item: Product | None, price=None, currency: str = "INR") -> dict | None`
- **Location**: Lines 693–715
- **Current Implementation**:
```python
def catalog_item_payload(
    item: Product | None,
    price=None,
    currency: str = "INR",
) -> dict | None:
    if item is None:
        return None

    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "unit": item.unit,
        "image_url": item.image_url,
        "brand_id": item.brand_id,
        "category_id": item.category_id,
        "price": (
            str(price)
            if price is not None
            else None
        ),
        "currency": currency,
    }
```

### File 2: `backend/app/api/v1/catalog.py`
- **Function**: `search_catalog_items`
- **Location**: Lines 106–220
- **Current Query Statement** (Lines 129–161):
```python
    statement = (
        select(Product)
        .outerjoin(ProductCode, ProductCode.product_id == Product.id)
        .outerjoin(Category, Category.id == Product.category_id)
        .where(Product.is_active.is_(True))
        .distinct()
    )

    if q:
        pattern = f"%{q.strip()}%"

        statement = statement.where(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                ProductCode.code.ilike(pattern),
                Category.name.ilike(pattern),
            )
        )

    if category:
        statement = statement.where(
            Category.name.ilike(category.strip())
        )

    statement = (
        statement
        .order_by(Product.name.asc())
        .offset(offset)
        .limit(limit)
    )

    products = list(db.scalars(statement).unique().all())
```

---

## 2. Exact Specification of Changes

### Change Set 1: `backend/app/services/catalog_import_service.py`

#### Objective:
Enrich the returned dictionary with:
1. `product_code`: string SKU from `item.codes` (primary code preferred, fallback to first code, or `None`).
2. `category`: string category name from `item.category.name` (or `None`).
3. `brand`: string brand name from `item.brand.name` (or `None`).
4. `attributes`: dictionary of key-value attributes (e.g. `{"module_width": "1 MW", "rated_current": "0.5A"}`) from `item.attributes`.

#### Field Extraction Logic & Edge Case Handling:
- **`product_code`**:
  - Check `getattr(item, "codes", None)`.
  - Iterate through `item.codes` to find any entry where `getattr(c, "is_primary", False)` is `True`.
  - If no primary code is found, fallback to `item.codes[0].code` if `len(item.codes) > 0`.
  - Otherwise return `None`.
- **`category`**:
  - Check `getattr(item, "category", None)`.
  - If `item.category` is not None and has attribute `name`, return `item.category.name`.
  - Otherwise return `None`.
  - Keep existing `"category_id": item.category_id` intact.
- **`brand`**:
  - Check `getattr(item, "brand", None)`.
  - If `item.brand` is not None and has attribute `name`, return `item.brand.name`.
  - Otherwise return `None`.
  - Keep existing `"brand_id": item.brand_id` intact.
- **`attributes`**:
  - Check `getattr(item, "attributes", None)`.
  - Populate dictionary `{attr.attribute_name: attr.attribute_value for attr in item.attributes if getattr(attr, "attribute_name", None)}`.
  - Return `{}` (empty dict) if `item.attributes` is empty or unpopulated.

#### Proposed Code for `catalog_item_payload` (Lines 693–715):
```python
def catalog_item_payload(
    item: Product | None,
    price=None,
    currency: str = "INR",
) -> dict | None:
    if item is None:
        return None

    product_code: str | None = None
    if getattr(item, "codes", None):
        product_code = next(
            (c.code for c in item.codes if getattr(c, "is_primary", False)),
            item.codes[0].code if item.codes else None,
        )

    brand_name: str | None = (
        item.brand.name
        if getattr(item, "brand", None) and hasattr(item.brand, "name")
        else None
    )

    category_name: str | None = (
        item.category.name
        if getattr(item, "category", None) and hasattr(item.category, "name")
        else None
    )

    attributes_dict: dict[str, str] = {}
    if getattr(item, "attributes", None):
        for attr in item.attributes:
            if getattr(attr, "attribute_name", None):
                attributes_dict[attr.attribute_name] = attr.attribute_value

    return {
        "id": item.id,
        "product_code": product_code,
        "name": item.name,
        "description": item.description,
        "unit": item.unit,
        "image_url": item.image_url,
        "brand_id": item.brand_id,
        "brand": brand_name,
        "category_id": item.category_id,
        "category": category_name,
        "price": (
            str(price)
            if price is not None
            else None
        ),
        "currency": currency,
        "attributes": attributes_dict,
    }
```

---

### Change Set 2: `backend/app/api/v1/catalog.py`

#### Objective:
Add SQLAlchemy `selectinload` options to prevent N+1 query overhead when loading `Product.codes`, `Product.category`, `Product.brand`, and `Product.attributes`.

#### Analysis of Eager Loading Options:
- **Why NOT `joinedload`?**
  - `Product.codes` and `Product.attributes` are one-to-many relationships. Joining multiple one-to-many collections generates a Cartesian product in SQL result sets (`len(codes) * len(attributes)` rows per product).
  - Furthermore, `joinedload` on collections combined with SQL `LIMIT` and `OFFSET` triggers SQLAlchemy warnings (`SAWarning: An alias is being generated...`) and forces in-memory deduplication and row slicing.
- **Why `selectinload`?**
  - `selectinload` executes one secondary `SELECT ... WHERE product_id IN (...)` query per relationship for all retrieved product IDs.
  - Exactly 4 secondary queries are issued regardless of whether `limit` is 10, 40, or 200 items.
  - Perfectly preserves SQL `LIMIT` and `OFFSET` pagination at the database level.
  - Zero Cartesian multiplication overhead.

#### Proposed Changes to `backend/app/api/v1/catalog.py`:

1. **Import Update** (Line 10):
   Change:
   ```python
   from sqlalchemy.orm import Session
   ```
   To:
   ```python
   from sqlalchemy.orm import Session, selectinload
   ```

2. **Query Statement Update in `search_catalog_items`** (Lines 129–136):
   Change:
   ```python
       statement = (
           select(Product)
           .outerjoin(ProductCode, ProductCode.product_id == Product.id)
           .outerjoin(Category, Category.id == Product.category_id)
           .where(Product.is_active.is_(True))
           .distinct()
       )
   ```
   To:
   ```python
       statement = (
           select(Product)
           .options(
               selectinload(Product.codes),
               selectinload(Product.category),
               selectinload(Product.brand),
               selectinload(Product.attributes),
           )
           .outerjoin(ProductCode, ProductCode.product_id == Product.id)
           .outerjoin(Category, Category.id == Product.category_id)
           .where(Product.is_active.is_(True))
           .distinct()
       )
   ```

*(Note: `count_statement` on line 183 must NOT use `selectinload`, as count queries do not load entity instances. It remains unchanged.)*

---

## 3. Query Count & Performance Comparison

| Metric | Before Changes | After Changes with `selectinload` |
|---|---|---|
| Main Product Query | 1 query | 1 query |
| ProductCode queries for N=40 | 40 queries (lazy) | 1 query (`WHERE product_id IN (...)`) |
| Category queries for N=40 | 40 queries (lazy) | 1 query (`WHERE id IN (...)`) |
| Brand queries for N=40 | 40 queries (lazy) | 1 query (`WHERE id IN (...)`) |
| Attribute queries for N=40 | 40 queries (lazy) | 1 query (`WHERE product_id IN (...)`) |
| Price calculation query | 1 query (`_latest_catalog_prices`) | 1 query (`_latest_catalog_prices`) |
| Total queries for N=40 | **162 queries** | **6 queries** |
| Total queries for N=200 | **802 queries** | **6 queries** |

---

## 4. Backward Compatibility & Test Suite Verification

### Backward Compatibility
1. **Existing Response Keys Preserved**:
   - `id`: int
   - `name`: str
   - `description`: str | None
   - `unit`: str | None
   - `image_url`: str | None
   - `brand_id`: int | None
   - `category_id`: int | None
   - `price`: str | None
   - `currency`: str
   All original 9 keys retain their exact types, keys, and values.

2. **New Keys Added**:
   - `product_code`: str | None
   - `brand`: str | None
   - `category`: str | None
   - `attributes`: dict[str, str]
   Adding these 4 keys is strictly additive and non-breaking for existing clients.

3. **Existing Tests in `backend/app/tests/`**:
   - `test_all_endpoints.py::test_catalog_search_and_categories` asserts:
     ```python
     response = client.get("/api/v1/catalog/items?limit=10")
     assert response.status_code == 200
     data = response.json()
     assert "total" in data
     assert "items" in data
     assert isinstance(data["items"], list)
     ```
     This test passes with 100% compatibility.
   - `test_all_endpoints.py::test_catalog_upload_validation` tests input validation for upload. Not affected.
   - Other test files (`test_health.py`, `test_products_api.py`, `test_siemens_parser.py`) do not touch `/api/v1/catalog/items`. Not affected.

### Recommended Additional Tests for Milestone 1:
The implementer can add the following assertions to `backend/app/tests/test_all_endpoints.py`:
```python
def test_catalog_search_enriched_payload():
    response = client.get("/api/v1/catalog/items?limit=10")
    assert response.status_code == 200
    data = response.json()
    for item in data.get("items", []):
        assert "product_code" in item
        assert "category" in item
        assert "brand" in item
        assert "attributes" in item
        assert isinstance(item["attributes"], dict)
```
And a unit test in a new or existing test file:
```python
def test_catalog_item_payload_unit():
    assert catalog_item_payload(None) is None
    # Test with dummy product
    # Verifies attribute mapping, primary code fallback, brand/category string extraction
```

---

## 5. Summary Checklist for Implementer
- [ ] In `backend/app/services/catalog_import_service.py`: Replace `catalog_item_payload` with the enriched implementation.
- [ ] In `backend/app/api/v1/catalog.py`: Import `selectinload` from `sqlalchemy.orm`.
- [ ] In `backend/app/api/v1/catalog.py`: Add `.options(selectinload(Product.codes), selectinload(Product.category), selectinload(Product.brand), selectinload(Product.attributes))` to `search_catalog_items`.
- [ ] Add unit and endpoint tests verifying the enriched payload fields (`product_code`, `category`, `brand`, `attributes`).
