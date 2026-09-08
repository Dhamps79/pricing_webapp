# Frontend Architecture & UI Investigation Survey Report

**Author**: `teamwork_preview_explorer_survey_2` (Explorer Agent)  
**Date**: 2026-09-08  
**Scope**: Frontend codebase, UI architecture, AG Grid configuration, header/toolbar controls, PDF catalog upload component, catalog pricing view, costing sheet workflow, and build/test status.

---

## 1. Executive Summary & Architectural Overview

The application was originally scaffolded as an online web-scraping price tracker ("Track product prices from online sources") with a simple table in AG Grid, a URL input toolbar (`POST /api/v1/prices/track`), and e-commerce tracker columns (`availability`, `trend`, `fetchedAt`, `targetPrice`).

Per authoritative specification `ORIGINAL_REQUEST.md`, the platform must be transformed into a **PDF Catalog Pricing and Costing Sheet management platform**, implementing:
- **R1**: Direct in-app PDF catalog uploading (`POST /api/v1/catalog/imports/upload`) with progress, states, and summary feedback.
- **R2**: Catalog pricing display connecting to `GET /api/v1/catalog/items` and `GET /api/v1/catalog/categories` with exact manufacturer prices (MRP/List Price), product codes, descriptions, units, and categories.
- **R3**: Interactive spreadsheet quotation costing sheet (`/api/v1/costing-sheets`) with live reactive calculations (`Line Net`, `List Total`, `Net Total`, `Grand Total`) and backend persistence.
- **R4**: Clean modern UI with zero vestigial web-scraping controls.

---

## 2. Frontend Tech Stack, Tooling, & Dependencies

### Package & Dependencies (`frontend/package.json`)
- **UI Framework**: React 19.2.8 (`react`, `react-dom`)
- **Grid Engine**: AG Grid Community 36.0.2 (`ag-grid-community`, `ag-grid-react`)
  - Modules: Registered via `ModuleRegistry.registerModules([AllCommunityModule])` in `src/main.tsx`.
- **Routing**: `react-router-dom` 7.11.0 (currently unused in single-page `App.tsx`, can be leveraged for tabs or view switching).
- **CSS / Styling**: `tailwindcss` 4.3.3, with custom CSS in `src/index.css` and `src/App.css`.
- **Bundler & Dev Server**: Vite 8.2.0 (`vite`) with `@vitejs/plugin-react` 6.0.4, `@rolldown/plugin-babel` 0.2.3, and `babel-plugin-react-compiler` 1.0.0.
- **TypeScript**: TypeScript ~6.0.2. Configuration in `tsconfig.json` and `tsconfig.app.json` has `target: es2023`, `verbatimModuleSyntax: true`, `erasableSyntaxOnly: true`, and `moduleResolution: bundler`.
- **Testing**: `vitest` 4.1.11, `jsdom` 30.0.1, `@testing-library/react` 16.3.3, `@testing-library/jest-dom` 7.0.1.
- **Linter**: `oxlint` 1.75.0.

### Scripts in `package.json`
- `"dev": "vite"`
- `"build": "tsc -b && vite build"`
- `"lint": "oxlint"`
- `"preview": "vite preview"`
- *Note*: `"test": "vitest run"` is currently missing from `package.json.scripts` and should be added for standardized test execution.

---

## 3. AG Grid Configuration & Current Spreadsheet Analysis

### Location & Setup (`frontend/src/components/PriceGrid.tsx`)
- Container: `<div className="ag-theme-quartz" style={{ width: "100%", height: "600px" }}>`
- Grid component: `<AgGridReact<ProductRow> rowData={rows} columnDefs={columnDefs} defaultColDef={defaultColDef} pagination={true} paginationPageSize={20} onCellValueChanged={...} />`
- Default ColDef: `{ resizable: true, sortable: true, filter: true }`

### Current Columns in `PriceGrid.tsx`
1. `name`: Product Name (`flex: 2`, `sortable`, `filter`)
2. `price`: Price (`sortable`, `filter: "agNumberColumnFilter"`, `valueFormatter` formatted with INR: `₹${Number(params.value).toLocaleString("en-IN")}`)
3. `currency`: Currency (`width: 100`, `sortable`, `filter`) — *vestigial*
4. `availability`: Availability (`flex: 1`, `sortable`, `filter`) — *vestigial*
5. `fetchedAt`: Last Updated (`flex: 1.5`, `sortable`, `filter`) — *vestigial*
6. `trend`: Trend (`width: 110`, `sortable`, `filter`) — *vestigial*
7. `quantity`: Quantity (`width: 110`, `editable: true`, `filter: "agNumberColumnFilter"`)
8. `targetPrice`: Target Price (`width: 130`, `editable: true`, `filter: "agNumberColumnFilter"`) — *vestigial*
9. `notes`: Notes (`flex: 1.5`, `editable: true`, `filter: true`)
10. `Total`: Value getter `price * quantity`
11. `Actions`: CellRenderer with "Refresh" (calls `onRefresh(productId)`) and "Delete" (calls `onDelete(productId)`) buttons — *Refresh is vestigial*.

### Critical Finding — Broken Type Definition:
`PriceGrid.tsx:4`, `App.tsx:5`, and `productMapper.ts:2` all import `ProductRow` from `./types/price` (or `../types/price`). However, inspecting `frontend/src/types/price.ts` reveals:
- Lines 1-39 only define `PriceHistoryItem`, `PriceHistoryResponse`, and `TrackedPriceResponse`.
- **`ProductRow` is completely absent from `types/price.ts`!**
- This results in TypeScript compilation errors under `tsc -b`.

---

## 4. Header/Toolbar Investigation & Vestigial Scrapers (R4)

### Current Layout in `frontend/src/App.tsx`
- **Header** (lines 376–392):
  ```tsx
  <header className="app-header">
    <div>
      <h1>Live Spreadsheet</h1>
      <p>Track product prices from online sources.</p>
    </div>
  </header>
  ```
- **Summary Cards** (lines 398–440): Total Products, Total Items, Total Current Value.
- **Toolbar Section** (lines 446–473):
  ```tsx
  <section className="toolbar">
    <input type="url" value={url} onChange={...} placeholder="Paste a product URL..." disabled={tracking} />
    <button type="button" onClick={handleTrack} disabled={tracking || !url.trim()}>
      {tracking ? "Tracking..." : "Track Price"}
    </button>
  </section>
  ```

### Vestigial Controls to REMOVE (per R4):
1. **URL Scraper input & button**: `<section className="toolbar">` URL input and "Track Price" button (`App.tsx:446–472`).
2. **Scraper subtitle text**: `<p>Track product prices from online sources.</p>` (`App.tsx:384–387`).
3. **Scraper state & methods in `App.tsx`**:
   - `url`, `setUrl`, `tracking`, `setTracking` (`App.tsx:21, 25`)
   - `handleTrack()` (`App.tsx:73–167`)
   - `handleRefresh()` (`App.tsx:174–260`)
4. **Scraper AG Grid columns & buttons**:
   - In `PriceGrid.tsx`: `currency`, `availability`, `fetchedAt`, `trend`, `targetPrice`, and `Actions -> Refresh`.
5. **Scraper API modules & endpoints**:
   - `frontend/src/api/prices.ts` (calls `POST /api/v1/prices/track`)
   - Scraper functions in `frontend/src/services/productApi.ts` (`refreshProduct`, `getPriceHistory`).

---

## 5. Catalog PDF Upload Integration Architecture (R1)

### Backend Endpoint Contract
- **Route**: `POST /api/v1/catalog/imports/upload`
- **Payload**: `multipart/form-data` with `file: File` (must be `.pdf`) and optional `supplier_name: string` (e.g. "Siemens").
- **Backend Response**:
  ```json
  {
    "id": 1,
    "file_name": "Electrical-Installation-Products.pdf",
    "supplier_name": "Siemens",
    "status": "completed",
    "total_rows": 52,
    "imported_rows": 52,
    "failed_rows": 0,
    "created_at": "2026-09-08T06:00:00Z",
    "completed_at": "2026-09-08T06:00:02Z"
  }
  ```
- **Status Polling Endpoint**: `GET /api/v1/catalog/imports/{import_id}`

### Proposed Component: `PdfUploadModal.tsx` / `PdfUploadToolbar.tsx`
- **Location**: In the top header/toolbar area, replacing the old URL input section.
- **Component UI Requirements**:
  1. **Upload Trigger**: "Upload Supplier Catalog PDF" button with file picker (`accept=".pdf"`), drag-and-drop file target area.
  2. **Supplier Field**: Optional input or auto-defaulted to "Siemens".
  3. **Visual Progress & States**:
     - `idle`: Ready for file selection.
     - `uploading`: Loading bar / spinner with "Uploading PDF...".
     - `processing`: "Extracting and parsing catalog products...".
     - `success`: Banner/toast showing:
       - File name
       - "Imported X products (Y failed)"
       - Elapsed time
     - `error`: Error banner showing backend error message (e.g., "Only PDF files are supported", "Uploaded PDF is empty").
  4. **Auto-Refresh Callback**: On upload success, immediately trigger catalog refresh (`onUploadSuccess`) so newly imported products appear in the grid without manual page reload.

---

## 6. Catalog Pricing Display & Data Retrieval (R2)

### Backend Endpoint Contracts
1. **Catalog Items**: `GET /api/v1/catalog/items?q={query}&category={category}&limit={limit}&offset={offset}`
   - Returns `{ "total": number, "items": CatalogItem[] }`
   - Item schema:
     ```ts
     export interface CatalogItem {
       id: number;
       name: string;
       description: string | null;
       unit: string | null;
       image_url: string | null;
       brand_id: number | null;
       category_id: number | null;
       price: string | null; // Exact manufacturer MRP / List Price (e.g. "925.00")
       currency: string;     // "INR"
     }
     ```
2. **Catalog Categories**: `GET /api/v1/catalog/categories`
   - Returns `{ "categories": string[] }` (e.g. `["Miniature Circuit Breakers (MCB)", "Residual Current Devices", ...]`)

### Frontend UI Integration
- **Toolbar Controls**:
  - **Category Filter Dropdown**: `<select>` dynamically populated from `GET /api/v1/catalog/categories`, with "All Categories" default.
  - **Text Search**: Search bar with real-time or debounced input querying `q` parameter (matches product codes, descriptions, category names).
- **AG Grid Catalog Columns**:
  1. **Product Code / SKU**: Extracted product reference (e.g. `5SL71057RC`).
  2. **Description / Name**: Product description (e.g. `5SL7 1P C0.5 7.5kA MCB`).
  3. **Category**: Category name.
  4. **Unit**: Unit of measure (e.g. `Nos`).
  5. **Manufacturer Price (MRP / List Price)**: Formatted currency `₹925.00`.
  6. **Action**: `+ Add to Quote` button to add item to the active Costing Sheet.

---

## 7. Costing Sheet / Quotation Integration (R3)

### Backend Endpoint Contracts
- `GET /api/v1/costing-sheets`: List existing sheets (`id`, `title`, `customer_name`, `discount_percent`, `line_count`, `updated_at`).
- `POST /api/v1/costing-sheets`: Create sheet (`title`, `customer_name`, `notes`, `discount_percent`).
- `GET /api/v1/costing-sheets/{id}`: Get full sheet with lines, line list total, line net total, grand total.
- `PATCH /api/v1/costing-sheets/{id}`: Update sheet metadata (`title`, `customer_name`, `discount_percent`, `notes`).
- `DELETE /api/v1/costing-sheets/{id}`: Delete sheet.
- `POST /api/v1/costing-sheets/{id}/lines`: Add product line (`product_id`, `quantity`, `sell_price`, `discount_percent`, `notes`).
- `PATCH /api/v1/costing-sheets/{id}/lines/{line_id}`: Update line (`quantity`, `sell_price`, `discount_percent`, `notes`).
- `DELETE /api/v1/costing-sheets/{id}/lines/{line_id}`: Delete line.

### Costing Sheet Schema (`CostingSheet` & `CostingSheetLine`):
```ts
export interface CostingSheetLine {
  id: number;
  product_id: number;
  sku: string | null;
  name: string;
  category: string | null;
  quantity: string;          // e.g. "10.00"
  unit: string | null;
  list_price: string;        // e.g. "500.00" (MRP)
  sell_price: string;        // e.g. "500.00"
  discount_percent: string;  // e.g. "10.00"
  line_list_total: string;   // e.g. "5000.00"
  line_net_total: string;    // e.g. "4500.00"
  notes: string | null;
  sort_order: number;
}

export interface CostingSheet {
  id: number;
  title: string;
  customer_name: string | null;
  notes: string | null;
  discount_percent: string;  // Sheet overall discount %
  list_total: string;
  net_total: string;
  grand_total: string;
  created_at: string;
  updated_at: string;
  lines: CostingSheetLine[];
}
```

### UI Workflow & Integration in the Spreadsheet
- **Navigation Structure**:
  - Two views / tabs:
    1. **Catalog Browser**: Browse & filter imported catalog products with direct "Add to Quote" button.
    2. **Costing Sheet / Quotation**: The interactive quotation spreadsheet editor.
  - Active Quote Bar: Displays current quote title, customer, and selector dropdown to switch quotes or create a new quote.
- **Costing Grid Columns (AG Grid)**:
  - `sku`: Product Code (read-only)
  - `name`: Description (read-only)
  - `category`: Category (read-only)
  - `unit`: Unit (read-only)
  - `list_price`: List Price / MRP (formatted `₹`, read-only)
  - `quantity`: Quantity (`editable: true`, numeric editor)
  - `discount_percent`: Discount % (`editable: true`, numeric editor 0–100%)
  - `sell_price`: Unit Sell Price (`editable: true`, defaults to `list_price * (1 - discount%)`)
  - `line_net_total`: Line Net Total (`valueGetter`: `sell_price * (1 - discount/100) * quantity`, formatted `₹`)
  - `notes`: Notes (`editable: true`)
  - `Actions`: Delete Line button
- **Live Automatic Calculation Logic**:
  - When a user edits `quantity`, `discount_percent`, or `sell_price`, client-side state recalculates immediately:
    $$\text{line\_list\_total} = \text{list\_price} \times \text{quantity}$$
    $$\text{line\_net\_total} = \text{sell\_price} \times (1 - \frac{\text{discount\_percent}}{100}) \times \text{quantity}$$
    $$\text{list\_total} = \sum \text{line\_list\_total}$$
    $$\text{net\_total} = \sum \text{line\_net\_total}$$
    $$\text{grand\_total} = \text{net\_total} \times (1 - \frac{\text{sheet\_discount}}{100})$$
  - Persistent sync: Debounced or on-blur call to `PATCH /api/v1/costing-sheets/{sheet_id}/lines/{line_id}`.
- **Quotation Summary Cards**:
  - Total Items / Lines
  - Total List Value (`₹`)
  - Total Net Value (`₹`)
  - Overall Discount (`%`)
  - Grand Total (`₹`)

---

## 8. Frontend Tests, Types, and Build Status

### Current Status:
1. **Build (`npm run build` / `tsc -b && vite build`)**:
   - **Failing**: Missing `ProductRow` in `frontend/src/types/price.ts`. TypeScript cannot compile `App.tsx`, `PriceGrid.tsx`, and `productMapper.ts`.
2. **Tests (`npx vitest run`)**:
   - Only 1 test file exists: `src/utils/productMapper.test.ts`.
   - Missing tests for PDF upload, catalog data fetching, category filter, costing calculations, and quotation persistence.
3. **Required Actions**:
   - Add `"test": "vitest run"` script to `package.json`.
   - Create comprehensive type definitions (`types/catalog.ts`, `types/costing.ts`).
   - Create unit tests for:
     - Catalog API & Costing API services
     - Live calculation helper (`calculateLineNet`, `calculateGrandTotal`)
     - Component render tests for Catalog and Costing Grid.

---

## 9. Proposed Frontend Component Architecture

```
frontend/src/
├── api/                  # Base API client
│   └── client.ts
├── components/
│   ├── Header.tsx        # Title, tab switcher (Catalog vs Costing Sheet)
│   ├── PdfUploadModal.tsx# PDF file selector, drag-drop, progress bar, summary
│   ├── CatalogToolbar.tsx# Search input, Category dropdown, Upload PDF button
│   ├── CatalogGrid.tsx   # AG Grid for catalog products with "Add to Quote"
│   ├── CostingToolbar.tsx# Quote selector, Customer name, Sheet discount %, New Quote btn
│   ├── CostingGrid.tsx   # AG Grid for quotation lines with live math
│   ├── CostingSummary.tsx# Summary cards: List Total, Net Total, Grand Total
│   └── Notification.tsx  # Toast / alert banners for upload feedback & errors
├── services/
│   ├── catalogApi.ts     # getCatalogItems, getCatalogCategories, uploadCatalogPdf
│   └── costingApi.ts     # CRUD for costing sheets and sheet lines
├── types/
│   ├── catalog.ts        # CatalogItem, CatalogCategory, ImportStatus
│   └── costing.ts        # CostingSheet, CostingSheetLine, CostingSheetCreate
└── utils/
    ├── calculations.ts   # Pure functions for line_net, list_total, grand_total
    └── calculations.test.ts # Vitest unit tests for calculations
```

---

## 10. Conclusion & Recommendations for Implementation

1. **Remove vestigial web-scraping artifacts**: Delete `src/api/prices.ts`, remove URL scraping input, scraper buttons, and scraper columns (`trend`, `availability`, etc.).
2. **Implement dedicated PDF Upload component**: Wire to `POST /api/v1/catalog/imports/upload` with progress, feedback card ("Imported X rows"), and auto-refresh.
3. **Connect Catalog View to Backend**: Fetch from `/api/v1/catalog/items` and `/api/v1/catalog/categories` with category filter dropdown and text search.
4. **Implement Quotation Costing Sheet**: Enable creating quotes, adding catalog items, editing quantity & discount, live calculation of totals, and persistence via `/api/v1/costing-sheets`.
5. **Ensure Test & Build Green**: Add `"test": "vitest run"` in `package.json`, fix TypeScript types, add calculation and component tests, and verify `npm run build` and `npx vitest run` succeed with zero errors.
