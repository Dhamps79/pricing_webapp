# Project: Live Spreadsheet PDF Catalog & Costing Sheet Management Platform

## Architecture
The application is a full-stack platform consisting of:
- **Backend (FastAPI + SQLAlchemy + SQLite/PostgreSQL)**:
  - `backend/app/api/v1/catalog.py`: Endpoints for PDF upload (`/imports/upload`), catalog search (`/items`), and categories (`/categories`).
  - `backend/app/api/v1/costing.py`: Full REST API for costing sheets and lines (`/costing-sheets`).
  - `backend/app/services/pdf_service.py` & `backend/app/services/parser/siemens_parser.py`: PDF text extraction using `pdfplumber` and coordinate clustering to parse manufacturer price lists (e.g. Siemens Betagard MCBs).
  - `backend/app/services/costing_service.py`: Exact mathematical calculations for Line Net, List Total, Net Total, Grand Total.
- **Frontend (React 19 + Vite + AG Grid Community + Tailwind CSS)**:
  - Header / Toolbar: PDF catalog upload component with progress, status, and summary metrics.
  - Navigation: View switcher between "Catalog Products" and "Quotation Costing Sheets".
  - Catalog AG Grid: Displays products with product code, description, category, unit, module width, and manufacturer MRP/List Price (₹), with category filter and search.
  - Costing Sheet AG Grid: Interactive quotation table with editable quantity and discount %, live reactive calculations, and backend persistence.
  - Notifications: Toast/banner system for status and errors.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | F1. PDF Upload Component | Dedicated drag-and-drop & file selector component in header/toolbar | M2 | ORIGINAL_REQUEST §R1 |
| 2 | F2. Upload Progress & Status | Real-time progress bar, states, and summary cards (imported/failed/time) | M2 | ORIGINAL_REQUEST §R1 |
| 3 | F3. Auto-Refresh on Upload | Automatic grid refresh upon successful catalog PDF upload | M2 | ORIGINAL_REQUEST §R1 |
| 4 | F4. Catalog API Integration | Frontend client for `GET /api/v1/catalog/items` and `/categories` | M3 | ORIGINAL_REQUEST §R2 |
| 5 | F5. Catalog Data & Pricing Integrity | Exact manufacturer prices (e.g. Siemens 5SL71057RC = ₹925.00), code, desc, unit, cat | M1, M3 | ORIGINAL_REQUEST §R2 |
| 6 | F6. Search & Category Filter | Category dropdown filter and text search for catalog products | M3 | ORIGINAL_REQUEST §R2 |
| 7 | F7. Costing Sheet Management | Create/select quotes, customer name, add catalog items to quote | M4 | ORIGINAL_REQUEST §R3 |
| 8 | F8. Reactive Quotation Calculations | Live client calculations for Line Net, List Total, Net Total, Grand Total | M4 | ORIGINAL_REQUEST §R3 |
| 9 | F9. Costing Backend Persistence | Full CRUD synchronization via `/api/v1/costing-sheets` | M4 | ORIGINAL_REQUEST §R3 |
| 10 | F10. Modern UI & Vestigial Cleanup | Remove obsolete scraping controls; responsive layout; toasts & loading states | M3, M4 | ORIGINAL_REQUEST §R4 |
| 11 | F11. Quality Verification & Test Suite | `npm run build`, `npx vitest run`, and `pytest -q` pass with zero errors | M1, M5 | ORIGINAL_REQUEST Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Catalog Enrichment & Frontend Build Fix | Enrich `catalog_item_payload` with product code, category name, attributes; fix frontend types & add test script | none | PLANNED |
| M2 | Catalog PDF Upload Integration | Dedicated upload component in header, progress states, summary feedback, auto-refresh | M1 | PLANNED |
| M3 | Catalog Pricing Display, Search & Scraper Cleanup | AG Grid catalog display with manufacturer prices, search, category filter, remove scrapers | M1 | PLANNED |
| M4 | Costing Sheet / Quotation Workflow | Quote management, catalog item selection, editable qty/discount, live calculations, API persistence | M2, M3 | PLANNED |
| M5 | E2E Testing, Adversarial Hardening & Final Gate | Full E2E test suite (Tiers 1-4), adversarial tests (Tier 5), verification of all test commands | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### Catalog Items Payload: `GET /api/v1/catalog/items`
```json
{
  "total": 120,
  "items": [
    {
      "id": 1,
      "product_code": "5SL71057RC",
      "name": "5SL71057RC",
      "description": "1P 5SL7 10kA C-Curve MCB 0.5A",
      "unit": "1 NO",
      "image_url": null,
      "brand_id": 1,
      "brand": "Siemens",
      "category_id": 2,
      "category": "MCB",
      "price": "925.00",
      "currency": "INR",
      "attributes": {
        "module_width": "1 MW",
        "rated_current": "0.5A"
      }
    }
  ]
}
```

### PDF Upload: `POST /api/v1/catalog/imports/upload`
- Request: `multipart/form-data` with `file: UploadFile`, `supplier_name: Optional[str]`.
- Response:
```json
{
  "id": 1,
  "file_name": "Electrical-Installation-Products.pdf",
  "supplier_name": "Siemens",
  "status": "COMPLETED",
  "total_rows": 52,
  "imported_rows": 52,
  "failed_rows": 0,
  "created_at": "2026-09-08T07:00:00Z",
  "completed_at": "2026-09-08T07:00:05Z"
}
```

### Costing Sheet API: `/api/v1/costing-sheets`
- Calculations:
  - `line_list_total = round(line.list_price * line.quantity, 2)`
  - `line_net_total = round(line.sell_price * (1 - line.discount_percent / 100) * line.quantity, 2)`
  - `sheet_list_total = round(sum(line.line_list_total for line in lines), 2)`
  - `sheet_net_total = round(sum(line.line_net_total for line in lines), 2)`
  - `grand_total = round(sheet_net_total * (1 - sheet.discount_percent / 100), 2)`

## Code Layout
### Backend
- `backend/app/api/v1/catalog.py`: Catalog upload, items search, categories endpoints.
- `backend/app/services/catalog_import_service.py`: `catalog_item_payload`, `upload_catalog_pdf`.
- `backend/app/api/v1/costing.py`: Costing sheets and lines API.
- `backend/app/services/costing_service.py`: Costing business logic and calculations.
- `backend/app/tests/`: Pytest test suite.

### Frontend
- `frontend/src/App.tsx`: Top-level application shell, header, view switching, toasts.
- `frontend/src/components/CatalogUpload.tsx`: PDF Upload component with drag-and-drop, progress, and summary modal/banner.
- `frontend/src/components/CatalogGrid.tsx`: AG Grid displaying catalog products, search, category filter.
- `frontend/src/components/CostingSheetView.tsx`: Quotation manager and editable AG Grid with reactive totals.
- `frontend/src/services/catalogApi.ts`: API client for catalog items, categories, and upload.
- `frontend/src/services/costingApi.ts`: API client for costing sheets and lines.
- `frontend/src/types/catalog.ts`: TypeScript definitions for catalog items, categories, and upload response.
- `frontend/src/types/costing.ts`: TypeScript definitions for costing sheets, lines, and calculations.
- `frontend/src/utils/calculations.ts`: Pure reactive math utility matching backend formulas.
- `frontend/src/utils/calculations.test.ts`: Vitest tests for financial/pricing math.
