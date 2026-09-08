# Handoff Report: Frontend UI Architecture & Survey Investigation

**Agent**: `teamwork_preview_explorer_survey_2`  
**Date**: 2026-09-08  
**Working Directory**: `c:\Users\BusinessComputers.in\Desktop\live-spreadsheet\.agents\teamwork_preview_explorer_survey_2`  
**Parent Conversation ID**: `1978d292-34f3-487b-bded-745eab8e629e`

---

## 1. Observation

1. **Framework, Build Tools, & Package Scripts**:
   - `frontend/package.json` (lines 12–36): Uses React 19.2.8 (`react`, `react-dom`), Vite 8.2.0 (`vite`), AG Grid Community 36.0.2 (`ag-grid-community`, `ag-grid-react`), Tailwind CSS 4.3.3 (`tailwindcss`), React Router DOM 7.11.0 (`react-router-dom`), Vitest 4.1.11 (`vitest`), and TypeScript ~6.0.2.
   - `frontend/package.json` (lines 6–11): Scripts defined are `"dev": "vite"`, `"build": "tsc -b && vite build"`, `"lint": "oxlint"`, `"preview": "vite preview"`. Missing `"test": "vitest run"`.
   - `frontend/src/main.tsx` (lines 1–2): Registers AG Grid community modules:
     ```ts
     import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
     ModuleRegistry.registerModules([AllCommunityModule]);
     ```

2. **Spreadsheet Component & Broken Types**:
   - `frontend/src/components/PriceGrid.tsx` (lines 29–164): AG Grid is set up with columns `name`, `price`, `currency`, `availability`, `fetchedAt`, `trend`, `quantity`, `targetPrice`, `notes`, `Total` (getter), and `Actions` (Refresh/Delete buttons).
   - `PriceGrid.tsx` (line 4), `App.tsx` (line 5), and `src/utils/productMapper.ts` (line 2) all import `import type { ProductRow } from "./types/price"`.
   - `frontend/src/types/price.ts` (lines 1–39): Contains only `PriceHistoryItem`, `PriceHistoryResponse`, and `TrackedPriceResponse`. `ProductRow` is completely missing from `types/price.ts`.

3. **Vestigial Web-Scraping Controls**:
   - `frontend/src/App.tsx` (lines 384–387): Subtitle reads `<p>Track product prices from online sources.</p>`.
   - `frontend/src/App.tsx` (lines 446–472): Toolbar has `<input type="url" value={url} ... placeholder="Paste a product URL..." />` and `<button onClick={handleTrack}>Track Price</button>`.
   - `frontend/src/App.tsx` (lines 73–167, 174–260): Contains `handleTrack()` calling `trackPrice` and `handleRefresh()` calling `refreshProduct`.
   - `frontend/src/api/prices.ts` (lines 4–16): Calls `POST /api/v1/prices/track?url=...`.
   - `frontend/src/services/productApi.ts` (lines 144–162): Calls `POST /api/v1/prices/{productId}/refresh` and `GET /api/v1/prices/{productId}/history`.

4. **Backend Catalog & Costing Endpoints**:
   - `backend/app/api/v1/catalog.py` (lines 35–97): `POST /api/v1/catalog/imports/upload` receives `file: UploadFile` and optional `supplier_name: str`, returning `id`, `file_name`, `supplier_name`, `status`, `total_rows`, `imported_rows`, `failed_rows`, `created_at`, `completed_at`.
   - `backend/app/api/v1/catalog.py` (lines 105–220): `GET /api/v1/catalog/items?q={}&category={}&limit={}&offset={}` returns `{ total: int, items: list }` with prices from `CatalogPrice`.
   - `backend/app/api/v1/catalog.py` (lines 227–258): `GET /api/v1/catalog/categories` returns `{ categories: list[str] }`.
   - `backend/app/api/v1/costing.py` (lines 54–170): Provides full costing sheet REST API: `GET /api/v1/costing-sheets`, `POST /api/v1/costing-sheets`, `GET /api/v1/costing-sheets/{id}`, `PATCH /api/v1/costing-sheets/{id}`, `DELETE /api/v1/costing-sheets/{id}`, `POST /api/v1/costing-sheets/{id}/lines`, `PATCH /api/v1/costing-sheets/{id}/lines/{line_id}`, `DELETE /api/v1/costing-sheets/{id}/lines/{line_id}`.
   - `backend/app/services/costing_service.py` (lines 20–87): Implements exact formula for calculations:
     - Line list: `list_price * quantity`
     - Line net: `sell_price * (1 - line_discount / 100) * quantity`
     - Grand total: `net_total * (1 - sheet_discount / 100)`.

5. **Frontend Testing & Build Status**:
   - `frontend/src/utils/productMapper.test.ts` (lines 1–31): Only existing test file, testing `productToRow`.
   - TypeScript build currently fails due to the missing `ProductRow` export in `types/price.ts`.

---

## 2. Logic Chain

1. From Observation 1 & 2: `App.tsx`, `PriceGrid.tsx`, and `productMapper.ts` depend on `ProductRow` from `types/price.ts`. Because `ProductRow` was omitted from `types/price.ts`, running `npm run build` (`tsc -b && vite build`) will fail type checking.
2. From Observation 3: The UI currently displays URL inputs, "Track Price" buttons, "Refresh" buttons, and columns for `availability`, `fetchedAt`, `trend`, and `targetPrice`. These are remnants of a generic scraper app and conflict directly with Requirement R4 ("without any vestigial web-scraping controls"). Removing these controls clean the UI and prepares the space for R1 and R2.
3. From Observation 3 & 4: Requirement R1 mandates a dedicated PDF upload component in the header/toolbar posting to `POST /api/v1/catalog/imports/upload`. The old scraper URL toolbar in `App.tsx` lines 446–472 is the optimal insertion point for this PDF upload component, which will feature drag-and-drop, upload progress states, summary cards (imported/failed rows), and an auto-refresh trigger.
4. From Observation 4: The backend exposes `GET /api/v1/catalog/items` and `GET /api/v1/catalog/categories`. In the existing code, `App.tsx` calls `getProducts()` (`/products`), which does not retrieve `CatalogPrice`. Transitioning data fetching to `/catalog/items` and `/catalog/categories` satisfies Requirement R2 by displaying exact manufacturer prices and populating the category dropdown.
5. From Observation 4: The costing backend endpoints in `backend/app/api/v1/costing.py` already support complete quotation workflows including line additions, updates, discounts, and deletions. Incorporating a dual-view or tabbed layout (Catalog Browser vs Quotation Costing Sheet) with an interactive AG Grid will satisfy Requirement R3, providing live reactive line net, list total, and grand total calculations synchronized with the backend.

---

## 3. Caveats

- Backend `catalog_item_payload` in `backend/app/services/catalog_import_service.py` (lines 701–715) returns `id`, `name`, `description`, `unit`, `image_url`, `brand_id`, `category_id`, `price`, `currency`. If the grid requires product code (SKU) and category name explicitly displayed in the catalog view, the backend payload or frontend mapping may need to supply `product_code` (from `product.codes`) and `category` (from `product.category.name`).
- We observed that running terminal commands triggers user approval timeouts in this environment, so all analysis was performed via code inspection and AST/grep verification.

---

## 4. Conclusion

The frontend requires:
1. **Cleanup**: Strip out all vestigial web-scraping code (URL input, "Track Price" button, scraper subtitle, scraper columns in AG Grid, `api/prices.ts`).
2. **R1 - PDF Upload**: Build a dedicated upload component in the header/toolbar posting multipart PDF to `POST /api/v1/catalog/imports/upload` with progress bar, processing states, import result metrics, and automatic grid refresh.
3. **R2 - Catalog Pricing Grid**: Build `services/catalogApi.ts` connecting to `GET /api/v1/catalog/items` and `GET /api/v1/catalog/categories`. Render AG Grid columns for Product Code, Description, Category, Unit, and MRP/List Price (₹). Provide category dropdown and debounced text search.
4. **R3 - Costing Sheet Workflow**: Build a dedicated Costing Sheet view with quote management (create/switch quotes, customer name, sheet discount), interactive quotation AG Grid with editable quantity/discount, client-side live reactive math matching backend `costing_service.py`, and persistence via `/api/v1/costing-sheets`.
5. **Quality & Tests**: Add `"test": "vitest run"` script to `package.json`, fix TypeScript types (`types/catalog.ts`, `types/costing.ts`), add calculation unit tests and component tests, ensuring `npm run build` and `npx vitest run` pass with zero errors.

---

## 5. Verification Method

To verify the observations and findings independently:
1. **Inspect Broken Type Import**:
   - Check `frontend/src/types/price.ts`: notice absence of `ProductRow`.
   - Check `frontend/src/components/PriceGrid.tsx:4` and `frontend/src/App.tsx:5`.
2. **Inspect Vestigial Controls**:
   - Inspect `frontend/src/App.tsx` lines 446–472 for URL input and "Track Price".
   - Inspect `frontend/src/components/PriceGrid.tsx` lines 51–81 for scraper columns.
3. **Inspect Backend Endpoint Definitions**:
   - Run `view_file` on `backend/app/api/v1/catalog.py` (lines 35–225) to verify `/imports/upload`, `/items`, and `/categories`.
   - Run `view_file` on `backend/app/api/v1/costing.py` (lines 54–170) to verify costing sheet routes.
4. **Inspect Calculation Formula**:
   - Run `view_file` on `backend/app/services/costing_service.py` (lines 20–87) to verify line net and grand total math.
