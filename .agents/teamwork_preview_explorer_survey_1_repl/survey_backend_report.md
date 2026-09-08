# Backend Architecture, Data Models, PDF Parser, and API Survey Report

**Date**: 2026-09-08  
**Author**: `teamwork_preview_explorer_survey_1_repl`  
**Workspace**: `c:\Users\BusinessComputers.in\Desktop\live-spreadsheet`  
**Working Directory**: `.agents\teamwork_preview_explorer_survey_1_repl`

---

## 1. Executive Summary

An in-depth investigation of the backend codebase located in `backend/` was conducted. The application is built with **FastAPI**, **SQLAlchemy ORM** (v2 syntax), and **PostgreSQL** (via `psycopg`). It contains a domain-tailored catalog import pipeline using **pdfplumber** coordinate clustering, a dedicated `CatalogPrice` structure distinct from online price tracking, and a quotation/costing sheet management module.

Key Findings:
1. **Catalog PDF Upload (`POST /api/v1/catalog/imports/upload`)**: Uploads and parses supplier PDFs synchronously within the request lifecycle. It saves the file to `storage/catalog/<uuid>.pdf`, extracts rows via coordinate-based parsing (`pdfplumber`), records import progress in `catalog_imports` and `catalog_import_rows`, and upserts `Product`, `ProductCode`, `ProductAttribute`, and `CatalogPrice` records.
2. **Catalog Items Retrieval (`GET /api/v1/catalog/items`)**: Searches active products joined with codes and categories, fetching the latest `CatalogPrice` via an SQL window function (`row_number() OVER (PARTITION BY product_id ORDER BY created_at DESC)`). **Critical Gap for R2**: `catalog_item_payload` currently omits `product_code`, `category` (string name), `brand` (string name), and structured `attributes` (e.g. `module_width`), which are required by the frontend AG Grid spreadsheet.
3. **Costing Sheet Workflow (`/api/v1/costing-sheets`)**: Fully implemented CRUD endpoints for sheets and lines with automatic lookup of latest catalog prices, live calculations for line net totals (`quantity * sell_price * (1 - line_discount/100)`), list total, net total, and grand total (`net_total * (1 - sheet_discount/100)`).
4. **Manufacturer PDF Parser (`siemens_parser.py` & `pdf_service.py`)**: Uses horizontal word clustering (`y_tolerance=2.0`) to project text into exact column bounds. Extracts Siemens references (e.g., `5SL71057RC`) and handles price notations like `925.-` or `₹925.00` converting into `Decimal("925")`.
5. **Backend Tests**: Located in `backend/app/tests/`. Main test suite `test_all_endpoints.py` tests Health, Products, Catalog search & upload validation, Costing Sheets lifecycle, and Prices SSRF. Test command is `pytest -q`.

---

## 2. Backend Routes and Endpoints Investigation

Mounted in `backend/app/main.py` via `backend/app/api/v1/router.py` with prefix `/api/v1`:

### 2.1 Catalog Endpoints (`backend/app/api/v1/catalog.py`)

| Method | Path | Request / Query | Response Structure | Behavior & Implementation |
|---|---|---|---|---|
| `POST` | `/api/v1/catalog/imports/upload` | Multipart form: `file: UploadFile` (must end with `.pdf`), `supplier_name: str` (optional) | `{"id": int, "file_name": str, "supplier_name": str, "status": str, "total_rows": int, "imported_rows": int, "failed_rows": int, "created_at": datetime, "completed_at": datetime}` | Reads contents into memory, validates `.pdf` and non-empty, calls `upload_catalog_pdf(db, contents=contents, original_filename=file.filename, supplier_name=supplier_name)`. Parses PDF synchronously and commits transaction. |
| `GET` | `/api/v1/catalog/items` | `q: str | None`, `category: str | None`, `limit: int = 40` (1-200), `offset: int = 0` | `{"total": int, "items": list[dict]}` | Searches active products matching `q` across `Product.name`, `Product.description`, `ProductCode.code`, `Category.name`. Filters by category if provided. Joins latest `CatalogPrice`. Returns paginated list. |
| `GET` | `/api/v1/catalog/categories` | None | `{"categories": list[str]}` | Returns alphabetically sorted distinct category names that have at least one active product. |
| `GET` | `/api/v1/catalog/imports/{import_id}` | `import_id: int` path param | `{"id": int, "file_name": str, "supplier_name": str, "effective_date": datetime, "status": str, "total_rows": int, "imported_rows": int, "failed_rows": int, "error_message": str, "created_at": datetime, "completed_at": datetime}` | Queries `CatalogImport` by PK; returns 404 if not found. |

### 2.2 Costing Sheet Endpoints (`backend/app/api/v1/costing.py`)

| Method | Path | Payload Schema | Response Schema | Description & Calculations |
|---|---|---|---|---|
| `GET` | `/api/v1/costing-sheets` | None | `list[CostingSheetSummary]` | Returns `[{"id": int, "title": str, "customer_name": str, "discount_percent": str, "updated_at": datetime, "line_count": int}]`. |
| `POST` | `/api/v1/costing-sheets` | `CostingSheetCreate`: `{title: str, customer_name?: str, notes?: str, discount_percent?: Decimal = 0}` | Serialized `CostingSheet` | Creates sheet, commits, returns full sheet with empty lines list and initial totals ("0.00"). |
| `GET` | `/api/v1/costing-sheets/{sheet_id}` | None | Serialized `CostingSheet` | Fetches sheet by ID with lines and products eagerly loaded. Returns 404 if not found. |
| `PATCH` | `/api/v1/costing-sheets/{sheet_id}` | `CostingSheetUpdate`: `{title?: str, customer_name?: str, notes?: str, discount_percent?: Decimal}` | Serialized `CostingSheet` | Updates metadata/discount, commits, recalculates `grand_total`. |
| `DELETE` | `/api/v1/costing-sheets/{sheet_id}` | None | `{"message": "Costing sheet deleted", "id": int}` | Deletes sheet (cascades to lines). Returns 404 if not found. |
| `POST` | `/api/v1/costing-sheets/{sheet_id}/lines` | `CostingLineCreate`: `{product_id: int, quantity?: Decimal = 1, sell_price?: Decimal, discount_percent?: Decimal = 0, notes?: str}` | Serialized `CostingSheet` | Adds line to sheet. If `sell_price` is None, auto-fetches latest catalog price from `CatalogPrice`. Recalculates all totals and returns updated sheet. |
| `PATCH` | `/api/v1/costing-sheets/{sheet_id}/lines/{line_id}` | `CostingLineUpdate`: `{quantity?: Decimal, sell_price?: Decimal, discount_percent?: Decimal, notes?: str}` | Serialized `CostingSheet` | Updates line quantity, sell price, discount, or notes. Recalculates totals. |
| `DELETE` | `/api/v1/costing-sheets/{sheet_id}/lines/{line_id}` | None | Serialized `CostingSheet` | Deletes specific line, commits, recalculates sheet totals. |

### 2.3 Other Mounted Endpoints
- **Health (`app/api/v1/health.py`)**:
  - `GET /api/v1/health`: returns `{"status": "ok"}`
  - `GET /api/v1/ready`: checks database connection, returns `{"status": "ready", "database": "ok"}`
- **Products (`app/api/v1/products.py`)**:
  - `POST /api/v1/products` (201), `GET /api/v1/products`, `GET /api/v1/products/{id}`, `PATCH /api/v1/products/{id}`, `DELETE /api/v1/products/{id}` (204), `GET /api/v1/products/{id}/history`.
- **Prices (`app/api/v1/prices.py`)**:
  - `POST /api/v1/prices/track?url=...` (legacy web scraping price tracker)
  - `GET /api/v1/prices/{product_id}`
  - `GET /api/v1/prices/{product_id}/history`
  - `POST /api/v1/prices/{product_id}/refresh`
  *(Per Requirement R4, these web-scraping features must NOT appear in the modern quotation and catalog UI).*

---

## 3. Data Models and ORM Architecture

Located in `backend/app/database/models/`:

### 3.1 Catalog Import Tables

1. **`CatalogImport` (`catalog_imports`)**:
   - `id`: Integer primary key, autoincrement.
   - `file_name`: String(255), original uploaded filename.
   - `file_path`: String(500), local filesystem path in `storage/catalog/<uuid>.pdf`.
   - `supplier_name`: String(150), default `"Siemens"`.
   - `effective_date`: DateTime(timezone=True), optional.
   - `status`: String(30), lifecycle: `"uploaded"` -> `"processing"` -> `"completed"` / `"completed_with_errors"` / `"failed"`.
   - `total_rows`: Integer, total products identified in PDF.
   - `imported_rows`: Integer, successfully imported product rows.
   - `failed_rows`: Integer, failed product rows.
   - `error_message`: Text, top-level failure reason.
   - `created_at`: DateTime(timezone=True), server_default `func.now()`.
   - `completed_at`: DateTime(timezone=True), timestamp when import finished.

2. **`CatalogImportRow` (`catalog_import_rows`)**:
   - `id`: Integer primary key.
   - `import_id`: ForeignKey(`catalog_imports.id`, ondelete="CASCADE"), indexed.
   - `page_number`: Integer, 1-based page number in PDF.
   - `row_number`: Integer, sequence index.
   - `raw_text`: Text, formatted debug string (e.g. `5SL71057RC | description | MRP=925 | STD_PKG=1/12`).
   - `parsed_status`: String(30), `"imported"`, `"failed"`, or `"pending"`.
   - `error_message`: Text.
   - `created_at`: DateTime.

### 3.2 Product & Catalog Structure

1. **`Product` (`products`)**:
   - `id`: Integer PK.
   - `name`: String(500), product description or fallback code.
   - `brand_id`: ForeignKey(`brands.id`, ondelete="SET NULL").
   - `category_id`: ForeignKey(`categories.id`, ondelete="SET NULL").
   - `description`: Text.
   - `unit`: String(50), e.g. `"Nos"`.
   - `image_url`: String(2000).
   - `is_active`: Boolean, default True.
   - Relationships:
     - `codes`: list[`ProductCode`], cascade="all, delete-orphan".
     - `attributes`: list[`ProductAttribute`], cascade="all, delete-orphan".
     - `brand`: `Brand | None`.
     - `category`: `Category | None`.
     - `costing_lines`: list[`CostingSheetLine`].

2. **`ProductCode` (`product_codes`)**:
   - `id`: Integer PK.
   - `product_id`: ForeignKey(`products.id`, ondelete="CASCADE").
   - `code`: String(100), unique, indexed (e.g. `"5SL71057RC"`).
   - `code_type`: String(50), e.g. `"manufacturer"`.
   - `is_primary`: Boolean, default False.

3. **`ProductAttribute` (`product_attributes`)**:
   - `id`: Integer PK.
   - `product_id`: ForeignKey(`products.id`, ondelete="CASCADE").
   - `attribute_name`: String(100), indexed (e.g. `"rated_current"`, `"module_width"`, `"section"`).
   - `attribute_value`: Text (e.g. `"0.5"`, `"1"`, `"1P, 240/415V AC"`).
   - UniqueConstraint on `("product_id", "attribute_name")`.

4. **`CatalogPrice` (`catalog_prices`)**:
   - `id`: Integer PK.
   - `product_id`: ForeignKey(`products.id`, ondelete="CASCADE"), indexed.
   - `import_id`: ForeignKey(`catalog_imports.id`, ondelete="CASCADE"), indexed.
   - `price`: Numeric(12, 2), unit list price / MRP from PDF (e.g. `925.00`).
   - `currency`: String(3), default `"INR"`.
   - `unit`: String(50), e.g. `"Nos"`.
   - `standard_package`: String(50), e.g. `"1/12"`.
   - `created_at`: DateTime.
   - *Architecture Note*: Deliberately separate from `price_history` (which is used for web-scraping). `CatalogPrice` represents printed manufacturer catalog prices.

5. **`Category` (`categories`)**:
   - `id`: Integer PK.
   - `name`: String(100), unique.
   - `description`: Text.
   - `is_active`: Boolean.

6. **`Brand` (`brands`)**:
   - `id`: Integer PK.
   - `name`: String(100), unique (e.g. `"Siemens"`).
   - `website`: String(255).
   - `is_active`: Boolean.

### 3.3 Costing Sheet Tables

1. **`CostingSheet` (`costing_sheets`)**:
   - `id`: Integer PK.
   - `title`: String(255), quote title.
   - `customer_name`: String(255), customer / client name.
   - `notes`: Text.
   - `discount_percent`: Numeric(6, 2), sheet-level discount (default 0.00).
   - `created_at`, `updated_at`: DateTime(timezone=True).
   - `lines`: list[`CostingSheetLine`], cascade="all, delete-orphan", ordered by `sort_order`.

2. **`CostingSheetLine` (`costing_sheet_lines`)**:
   - `id`: Integer PK.
   - `costing_sheet_id`: ForeignKey(`costing_sheets.id`, ondelete="CASCADE"), indexed.
   - `product_id`: ForeignKey(`products.id`, ondelete="RESTRICT"), indexed.
   - `quantity`: Numeric(12, 2), default 1.00.
   - `list_price`: Numeric(14, 2), snapshot unit catalog/MRP price.
   - `sell_price`: Numeric(14, 2), quotation unit price before line discount.
   - `discount_percent`: Numeric(6, 2), line-level discount percent.
   - `unit`: String(50).
   - `notes`: Text.
   - `sort_order`: Integer, default 0.
   - `created_at`: DateTime(timezone=True).

---

## 4. PDF Catalog Parser Implementation

### 4.1 Parser Files & Responsibilities
- `backend/app/services/pdf_service.py`: Low-level PDF coordinate extractor.
- `backend/app/services/parser/siemens_parser.py`: Siemens-specific table extractor and domain object builder.
- `backend/app/services/catalog_parser_service.py`: Product code and price text normalizer.
- `backend/app/services/catalog_import_service.py`: Orchestrator of storage, parsing, and database transactions.

### 4.2 Coordinate Extraction & Horizontal Clustering
In `pdf_service.py`:
1. Opens PDF with `pdfplumber.open(path)`.
2. For each page, runs `page.extract_words()`.
3. Maps each word to `CoordinateWord` with `x0`, `y0` (top), `x1`, `y1` (bottom), `x_center`, and `y_center`.
4. `_cluster_words_into_rows` sorts words vertically and clusters words whose `abs(word.y_center - row.y_center) <= 2.0` (`y_tolerance`).
5. Returns `CoordinateRow` objects containing horizontal words in reading order (`word.x0`).

### 4.3 Table Layout Projection
In `siemens_parser.py`:
`row_to_cells(row, columns)` maps words into column bins by checking `column.x0 <= word.x_center < column.x1`:
- **MCB Columns (`MCB_COLUMNS`)**:
  - `section`: x in [40, 245)
  - `rated_current`: x in [245, 310)
  - `mw` (Module Width): x in [310, 350)
  - `reference_no`: x in [350, 435)
  - `mrp`: x in [435, 495)
  - `standard_package`: x in [495, 560)
- **DOL Columns (`DOL_COLUMNS`)**:
  - `hp` (90-125), `kw` (125-155), `starter` (155-220), `contactor` (220-310), `overload_relay` (310-365), `relay_range` (365-400), `max_full_load_current` (400-460), `mrp` (460-515), `standard_package` (515-550).

### 4.4 Reference Number & Price Parsing (Siemens 5SL71057RC ₹925.00)
1. **Reference Number**:
   - `SIEMENS_REFERENCE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\-/^#]{5,}$", re.IGNORECASE)`
   - Matches alphanumeric codes (length >= 6) without spaces, e.g. `5SL71057RC`.
2. **Price Parsing (`catalog_parser_service.parse_price`)**:
   - Handles Siemens price notation: `925.-` -> strips `.-`.
   - Cleans formatting characters: commas, spaces, `Rs.`, and `₹`.
   - Uses `re.search(r"\d+(?:\.\d+)?", value)` and converts to `Decimal("925")`.
   - Stored in `CatalogPrice` with `price=Decimal("925.00")`, `currency="INR"`, `standard_package="1/12"`.
3. **Table Detection (`detect_table_type`)**:
   - Dynamic page text detection:
     - MCB table: `"reference"` and `"mrp"` both present in page text.
     - DOL table: `"starter"`, `"contactor"`, and `"thermal"` present.
     - Unsupported pages return `[]` and are skipped safely.
4. **Synchronous vs Asynchronous Execution**:
   - **Fully synchronous**: `POST /api/v1/catalog/imports/upload` executes `upload_catalog_pdf` in the HTTP thread/process.
   - It completes extraction and DB transactions, returning the summary in the initial HTTP response.
   - There are **no** background task queues (Celery, RQ, etc.). `GET /api/v1/catalog/imports/{import_id}` exists for querying historical import status.

---

## 5. Costing Calculations Deep Dive

In `costing_service.py`:
- **Line Net Total (`line_net_total`)**:
  $$\text{discount} = \frac{\text{line.discount\_percent}}{100}$$
  $$\text{unit\_net} = \text{line.sell\_price} \times (1 - \text{discount})$$
  $$\text{line\_net} = \text{round}(\text{unit\_net} \times \text{line.quantity}, 2)$$
- **Sheet List Total (`list_total`)**:
  $$\text{list\_total} = \sum (\text{round}(\text{line.list\_price} \times \text{line.quantity}, 2))$$
- **Sheet Net Total (`net_total`)**:
  $$\text{net\_total} = \sum \text{line\_net}$$
- **Sheet Grand Total (`grand_total`)**:
  $$\text{sheet\_discount} = \frac{\text{sheet.discount\_percent}}{100}$$
  $$\text{grand\_total} = \text{round}(\text{net\_total} \times (1 - \text{sheet\_discount}), 2)$$

In `serialize_sheet`, each line includes: `id`, `product_id`, `sku`, `name`, `category`, `quantity`, `unit`, `list_price`, `sell_price`, `discount_percent`, `line_list_total`, `line_net_total`, `notes`, `sort_order`.

---

## 6. Backend Test Suite Investigation

- Test folder: `backend/app/tests/`
- Test command:
  ```powershell
  pytest -q
  ```
  *(run in `backend/` directory)*

### Test Files Breakdown:
1. `test_all_endpoints.py` (270 lines):
   - Health & readiness: checks `/api/v1/health` (200), `/api/v1/ready` (200, db ok).
   - Products CRUD: create, duplicate conflict (409), get by id, search (`?q=...`), patch description/unit, price history endpoint, delete (204), 404 on deleted.
   - Catalog: `GET /api/v1/catalog/items?limit=10` (asserts `total` and `items`), `GET /api/v1/catalog/categories` (asserts `categories`), upload validation for non-PDF (400) and empty PDF (400), 404 for missing import ID.
   - Costing sheets lifecycle: creates sheet, lists sheets, adds product line, verifies `line_net_total` and `grand_total`, patches line quantity/discount, patches sheet discount, deletes line, deletes sheet, verifies 404.
   - Prices SSRF protection: verifies SSRF blocking on private IP / localhost targets.
2. `test_siemens_parser.py` (21 lines):
   - Tests `is_siemens_reference` for valid (`5SL41020RC`, `5SU13247RC32`) and invalid (`16A`) codes.
3. `test_products_api.py` (10 lines):
   - Asserts routes `/api/v1/products` and `/api/v1/products/{product_id}` exist in `app.openapi()["paths"]`.
4. `test_health.py` (18 lines):
   - Tests `GET /api/v1/health`.
5. Empty stub test files:
   - `test_brand.py` (0 bytes)
   - `test_categories.py` (0 bytes)
   - `test_products.py` (0 bytes)

---

## 7. Gap Analysis for Requirements R1, R2, R3, R4

| Requirement | Current Backend State | Gap / Needed Fix / Action |
|---|---|---|
| **R1: Catalog PDF Upload** | `POST /api/v1/catalog/imports/upload` accepts `.pdf` files, parses synchronously, records row stats in `catalog_imports`, returns `{id, file_name, status, total_rows, imported_rows, failed_rows, created_at, completed_at}`. | **Backend works as expected.** Response has all needed fields. Frontend needs to send `multipart/form-data` and display real-time status and row summary. |
| **R2: Catalog Pricing Display & Data Retrieval** | `GET /api/v1/catalog/items` returns `items` and `total`. `_latest_catalog_prices` fetches latest `CatalogPrice`. | **CRITICAL GAP**: `catalog_item_payload` in `backend/app/services/catalog_import_service.py:693-715` only serializes `id`, `name`, `description`, `unit`, `image_url`, `brand_id`, `category_id`, `price`, `currency`. **It does NOT include `product_code` (or `sku`), `category` (string name), `brand` (string name), or `attributes` (e.g. `module_width`).** For R2, `product_code`, `category`, and `attributes` / `module_width` must be returned so the spreadsheet can display them without extra queries. Also `search_catalog_items` in `catalog.py` should eagerly load `codes`, `category`, `brand`, and `attributes`. |
| **R3: Costing Sheet Workflow** | Complete endpoints `/api/v1/costing-sheets` and `.../lines` with automatic catalog price fallback, line net, list total, net total, grand total. | **Backend is complete.** Frontend needs to connect the spreadsheet costing UI to these endpoints. |
| **R4: Polished Modern UI & Error Resilience** | Backend `/api/v1/prices/track` exists from legacy web scraping. | Backend requires no changes for R4. Frontend must omit URL scraping inputs and buttons, focusing exclusively on catalog and costing sheet interfaces. |
