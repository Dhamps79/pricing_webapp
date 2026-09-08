## 2026-09-08T07:07:32Z
You are worker_m1, the implementation specialist for Milestone 1: Backend Catalog Enrichment & Frontend Build Fix.
Your working directory is: c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\worker_m1
Workspace root: c:\Users\BusinessComputers.in\Desktop\live-spreadsheet
Parent conversation ID: 1978d292-34f3-487b-bded-745eab8e629e

MANDATORY FIRST STEP:
Read the authoritative user request at:
c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\ORIGINAL_REQUEST.md
And read the project architecture at:
c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\PROJECT.md

MANDATORY EXPLORER FINDINGS TO READ BEFORE IMPLEMENTING:
1. c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\teamwork_preview_explorer_m1_1\plan_backend_enrichment.md
2. c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\teamwork_preview_explorer_m1_2\plan_frontend_types.md
3. c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\teamwork_preview_explorer_m1_3\plan_verification.md

WRITE OWNERSHIP (Exclusively owned files for Milestone 1):
- backend/app/services/catalog_import_service.py
- backend/app/api/v1/catalog.py
- frontend/src/types/price.ts
- frontend/src/types/catalog.ts
- frontend/src/types/costing.ts
- frontend/package.json
- backend/app/tests/test_catalog_payload.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

OBJECTIVES & TASKS:
1. In `backend/app/services/catalog_import_service.py`:
   Update `catalog_item_payload(item: Product | None, price=None, currency: str = "INR")` to extract and include:
   - `product_code`: primary code from `item.codes` (or first code fallback, or None)
   - `category`: string name from `item.category.name` (or None)
   - `brand`: string name from `item.brand.name` (or None)
   - `attributes`: dictionary of `{attr.attribute_name: attr.attribute_value for attr in item.attributes}`
   Preserve all 9 existing keys (`id`, `name`, `description`, `unit`, `image_url`, `brand_id`, `category_id`, `price`, `currency`). Use safe `getattr` checks.
2. In `backend/app/api/v1/catalog.py`:
   Import `selectinload` from `sqlalchemy.orm`.
   Add `.options(selectinload(Product.codes), selectinload(Product.category), selectinload(Product.brand), selectinload(Product.attributes))` to the main `statement` in `search_catalog_items`.
3. In `frontend/src/types/price.ts`:
   Export interface `ProductRow` with all 16 required fields so `tsc -b` compiles without errors (ensure `currency: string | null`, and include `trend: PriceTrend` imported from `./product`).
4. In `frontend/src/types/catalog.ts`:
   Create complete TypeScript interfaces for `CatalogItem`, `CatalogResponse`, `CatalogUploadResponse`, `CatalogQueryParams`, `CatalogItemAttributes`, `CatalogRow`.
5. In `frontend/src/types/costing.ts`:
   Create complete TypeScript interfaces for `CostingSheetLine`, `CostingSheet`, `CostingTotals`, `CostingSheetCreate`, `CostingLineCreate`, `CostingLineUpdate`.
6. In `frontend/package.json`:
   Add `"test": "vitest run"` under `"scripts"`.
7. In `backend/app/tests/test_catalog_payload.py`:
   Implement unit tests for `catalog_item_payload` covering complete product with relationships, missing optional relationships, and None product.
8. Execute verification:
   - Run `npm run build` in `frontend/` (verify exit code 0).
   - Run `npx vitest run` in `frontend/` (verify tests pass).
   - Run `pytest -q` in `backend/` using `backend\.webapp\Scripts\pytest.exe` (verify 100% pass).
   Record the exact commands and outputs.
