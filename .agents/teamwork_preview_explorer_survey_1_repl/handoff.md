# Handoff Report: Backend Architecture, APIs, Models, Parser, and Test Survey

**Agent**: `teamwork_preview_explorer_survey_1_repl`  
**Handoff Type**: Hard (Task complete)  
**Target Path**: `c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\teamwork_preview_explorer_survey_1_repl\handoff.md`  
**Date**: 2026-09-08  

---

## 1. Observation

1. **Backend Routing & Entry Points**:
   - `backend/app/main.py:25-28` mounts `api_router` with prefix `/api/v1`.
   - `backend/app/api/v1/router.py:12-16` includes `prices_router`, `products_router`, `catalog_router`, `costing_router`, and `health_router`.
   - `backend/app/api/v1/catalog.py:35` declares `@router.post("/imports/upload")`.
   - `backend/app/api/v1/catalog.py:105` declares `@router.get("/items")`.
   - `backend/app/api/v1/catalog.py:227` declares `@router.get("/categories")`.
   - `backend/app/api/v1/catalog.py:265` declares `@router.get("/imports/{import_id}")`.
   - `backend/app/api/v1/costing.py:54-169` declares `@router.get("")`, `@router.post("")`, `@router.get("/{sheet_id}")`, `@router.patch("/{sheet_id}")`, `@router.delete("/{sheet_id}")`, `@router.post("/{sheet_id}/lines")`, `@router.patch("/{sheet_id}/lines/{line_id}")`, and `@router.delete("/{sheet_id}/lines/{line_id}")`.

2. **Catalog Import Execution & Parser**:
   - In `backend/app/services/catalog_import_service.py:569-625`:
     ```python
     def upload_catalog_pdf(db: Session, *, contents: bytes, original_filename: str, ...):
         _, stored_path = save_catalog_pdf(contents=contents, original_filename=original_filename)
         import_record = CatalogImport(...)
         db.add(import_record)
         db.flush()
         try:
             import_siemens_catalog(db, import_record=import_record)
             db.commit()
             db.refresh(import_record)
             return import_record
     ```
     Execution is synchronous. It runs within the HTTP request handler without any background worker queue (no Celery/BackgroundTasks).
   - In `backend/app/services/pdf_service.py:130-213`, PDF text is extracted using `pdfplumber.open(path)` and `page.extract_words()`. Words are clustered horizontally into `CoordinateRow`s using `y_tolerance = 2.0`.
   - In `backend/app/services/parser/siemens_parser.py:58-65`, `MCB_COLUMNS` maps columns:
     ```python
     MCB_COLUMNS = (
         Column("section", 40, 245),
         Column("rated_current", 245, 310),
         Column("mw", 310, 350),
         Column("reference_no", 350, 435),
         Column("mrp", 435, 495),
         Column("standard_package", 495, 560),
     )
     ```
   - In `backend/app/services/catalog_parser_service.py:65-94`, `parse_price` strips `.-`, commas, `Rs.`, `₹`, and extracts decimal with `re.search(r"\d+(?:\.\d+)?", value)` to parse values like `925.-` or `₹925.00` into `Decimal("925")`.
   - In `backend/app/services/catalog_import_service.py:481-524`, each row is imported within `with db.begin_nested():`, upserting `Product`, `ProductCode`, `ProductAttribute`, `CatalogPrice`, and `CatalogImportRow`.

3. **Catalog Item Payload Omission (R2 Gap)**:
   - In `backend/app/services/catalog_import_service.py:693-715`:
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
     `product_code`, `category` (string name), `brand` (string name), and `attributes` (e.g. `module_width`) are not returned in this payload.

4. **Costing Sheet Calculations & Serializer**:
   - In `backend/app/services/costing_service.py:20-87`:
     - Line Net: `(line.sell_price * (1 - line.discount_percent/100) * line.quantity).quantize(Decimal("0.01"))`.
     - List Total: `sum((line.list_price * line.quantity).quantize(Decimal("0.01")))`.
     - Net Total: `sum(line_net)`.
     - Grand Total: `(net_total * (1 - sheet.discount_percent/100)).quantize(Decimal("0.01"))`.
     - Lines include `product_id`, `sku`, `name`, `category`, `quantity`, `unit`, `list_price`, `sell_price`, `discount_percent`, `line_list_total`, `line_net_total`, `notes`, `sort_order`.

5. **Test Files**:
   - `backend/app/tests/test_all_endpoints.py` (270 lines) tests all endpoints across health, products, catalog, costing sheets, and prices SSRF.
   - `backend/app/tests/test_siemens_parser.py` (21 lines) tests Siemens reference parsing.
   - `backend/app/tests/test_health.py` (18 lines) and `backend/app/tests/test_products_api.py` (10 lines).
   - Empty files: `test_brand.py`, `test_categories.py`, `test_products.py`.

---

## 2. Logic Chain

1. **R1 Evaluation**:
   - Observation 1 & 2 show `POST /api/v1/catalog/imports/upload` receives multipart PDF uploads, parses them via `upload_catalog_pdf`, writes row status to `catalog_import_rows`, and returns `{id, file_name, supplier_name, status, total_rows, imported_rows, failed_rows, created_at, completed_at}`.
   - Because execution is synchronous, the HTTP client gets the complete import statistics upon request termination.
   - Therefore, the backend endpoint for R1 is functional and fulfills R1 requirements.

2. **R2 Evaluation**:
   - Observation 3 shows `catalog_item_payload` produces only `{id, name, description, unit, image_url, brand_id, category_id, price, currency}`.
   - R2 explicitly requires the AG Grid spreadsheet to display: exact manufacturer prices (MRP/List Price), product codes, descriptions, units, categories, and module width/attributes.
   - Because `product_code`, `category` (name), and attributes (e.g. `module_width`) are not present in the payload returned by `GET /api/v1/catalog/items`, the frontend grid cannot display these columns without updating `catalog_item_payload` and ensuring eager loading (`selectinload(Product.codes)`, `selectinload(Product.category)`, `selectinload(Product.attributes)`) in `search_catalog_items`.

3. **R3 Evaluation**:
   - Observation 4 shows `/api/v1/costing-sheets` CRUD endpoints and `/lines` operations are fully implemented in `costing.py` and `costing_service.py`.
   - When adding a line without `sell_price`, it automatically looks up the latest `CatalogPrice` from `latest_catalog_prices_for_products`.
   - Computations for Line Net, List Total, Net Total, and Grand Total are implemented with exact Decimal rounding.
   - Therefore, R3 backend capabilities are complete and ready for frontend integration.

4. **R4 Evaluation**:
   - Observation 1 shows `/prices` router handles URL tracking and web scraping. R4 requires removing vestigial web-scraping controls from the modern UI, which is entirely a frontend adjustment since the backend `/catalog` and `/costing-sheets` routes are decoupled from `/prices`.

---

## 3. Caveats

- Database migrations in `alembic/versions` were reviewed and are consistent with current models (`CatalogImport`, `CatalogPrice`, `CostingSheet`, etc.).
- Active PostgreSQL connection was not directly queried via interactive shell due to explorer read-only constraints, but ORM definitions and test fixtures in `test_all_endpoints.py` were verified by reading source code directly.
- No caveats regarding backend route inventory, schema completeness, or parser algorithm.

---

## 4. Conclusion

The backend has robust core infrastructure for PDF catalog parsing (`pdfplumber` + coordinate clustering in `siemens_parser.py`) and quotation sheet calculations (`costing_service.py`).
To fully support R1-R4:
1. **Catalog Payload Enrichment**: `backend/app/services/catalog_import_service.py:catalog_item_payload` must be enhanced to serialize `product_code` (primary code from `item.codes`), `category` (name from `item.category`), `brand` (name from `item.brand`), and attributes (`module_width` from `item.attributes`).
2. **Eager Loading**: `backend/app/api/v1/catalog.py:search_catalog_items` should use `selectinload` for `Product.codes`, `Product.category`, and `Product.attributes` to avoid N+1 queries when building the enriched item payloads.
3. **Frontend Integration**: Frontend can directly post files to `POST /api/v1/catalog/imports/upload`, fetch catalog items and categories from `GET /api/v1/catalog/items` and `GET /api/v1/catalog/categories`, and drive the quotation workflow using `/api/v1/costing-sheets`.

---

## 5. Verification Method

1. **Inspect Target Files & Lines**:
   - `backend/app/api/v1/catalog.py`: Lines 35-97 (upload), 105-220 (items search), 227-258 (categories).
   - `backend/app/services/catalog_import_service.py`: Lines 693-715 (`catalog_item_payload`).
   - `backend/app/api/v1/costing.py`: Lines 25-170 (costing sheets routes).
   - `backend/app/services/costing_service.py`: Lines 20-87 (pricing math and serialization).
   - `backend/app/services/parser/siemens_parser.py`: Lines 58-65 (columns) and 499-528 (document parser).
2. **Run Backend Test Suite**:
   ```powershell
   cd backend
   pytest -q
   ```
   Expected: All test cases in `app/tests/test_all_endpoints.py`, `app/tests/test_siemens_parser.py`, `app/tests/test_products_api.py`, and `app/tests/test_health.py` execute.
3. **Invalidation Conditions**:
   - If `catalog_item_payload` is modified to already contain `product_code`, `category`, and `attributes`, the identified R2 payload gap is resolved.
   - If a background worker is introduced for `upload_catalog_pdf`, the synchronous execution model finding is superseded.
