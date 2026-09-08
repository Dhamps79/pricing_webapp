# Original User Request

## 2026-09-08T06:42:33Z

<USER_REQUEST>
Transform the Live Spreadsheet web application into a polished PDF Catalog Pricing and Costing Sheet management platform, featuring direct in-app PDF catalog uploading, accurate catalog price retrieval matching imported manufacturer PDFs, and interactive spreadsheet-style quotation costing.

Working directory: c:\Users\BusinessComputers.in\Desktop\live-spreadsheet
Integrity mode: development

## Requirements

### R1. Catalog PDF Upload Integration
Provide a dedicated, intuitive upload component in the frontend header/toolbar that allows users to upload supplier catalog PDFs directly to `POST /api/v1/catalog/imports/upload`, displaying real-time upload progress, processing states, and summary feedback (e.g. imported rows, failed rows, elapsed time) with error handling.

### R2. Catalog Pricing Display & Data Retrieval
Connect the spreadsheet view to the catalog API (`GET /api/v1/catalog/items` and `/api/v1/catalog/categories`) so that all imported catalog products are retrieved and displayed in the AG Grid spreadsheet with their exact manufacturer prices (MRP/List Price), product codes, descriptions, units, and categories directly reflecting the imported PDF catalogs.

### R3. Costing Sheet / Quotation Workflow
Integrate the costing sheet capabilities (`/api/v1/costing-sheets`) into the spreadsheet interface so users can create quotes, select catalog items, adjust quantities and discounts with live automatic calculations (Line Net, List Total, Net Total, Grand Total), and manage quotation lines.

### R4. Polished Modern UI & Error Resilience
Deliver a clean, responsive, and polished user interface with clean visual hierarchy, loading states, search/category filtering, toast/banner notifications for upload events and errors, without any vestigial web-scraping controls.

## Acceptance Criteria

### PDF Upload Workflow
- [ ] The frontend provides an interactive PDF file selector/drag-and-drop button that posts files to `/api/v1/catalog/imports/upload`.
- [ ] During and after upload, user is shown import progress and status (e.g. "Imported 52 rows").
- [ ] Upon successful upload, the catalog spreadsheet automatically refreshes with the newly imported products.

### Catalog Data & Pricing Integrity
- [ ] Prices shown in the spreadsheet grid match the exact unit MRP/LP from the imported PDFs (e.g., Siemens 5SL71057RC shows ₹925.00).
- [ ] Product code, description, module width/attributes, category, and unit are accurately displayed.
- [ ] Category dropdown filter and text search allow instant filtering of catalog products.

### Costing Sheet Integration
- [ ] Users can create a new costing sheet, add items from the catalog, edit quantities and discount percentages in the spreadsheet, and see totals update reactively.
- [ ] Costing sheet changes are persisted via the backend costing API.

### Verification & Testing
- [ ] Automated frontend tests (`npm run build` and `npx vitest run`) pass with zero errors.
- [ ] Backend test suite (`pytest -q`) continues to pass 100%.
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-09-08T12:12:33+05:30.
</ADDITIONAL_METADATA>
