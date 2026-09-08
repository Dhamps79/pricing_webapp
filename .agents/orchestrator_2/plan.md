# Orchestration Plan (Generation 2)

## Goal
Transform Live Spreadsheet into a polished PDF Catalog Pricing and Costing Sheet management platform, fulfilling all requirements (R1, R2, R3, R4) and acceptance criteria.

---

## Milestone Execution Pipeline

### Milestone 2: Catalog PDF Upload Integration (R1)
- **Objective**: Implement intuitive drag-and-drop & file selector in the frontend header/toolbar posting to `POST /api/v1/catalog/imports/upload`. Show real-time upload progress, processing status, summary feedback (imported rows, failed rows, elapsed time), error handling, and trigger grid auto-refresh.
- **Iteration Cycle**:
  1. Explorers (3 parallel): Analyze existing upload endpoint, frontend header/toolbar architecture, AG Grid refresh hooks, and create execution blueprint.
  2. Worker: Implement `CatalogUpload.tsx` component, upload service API client, progress/summary state, error toasts, and event hook for grid refresh. Run `npm run build` and `npx vitest run`.
  3. Reviewers (2 parallel): Inspect UI structure, drag-and-drop, API payload compliance, build/test results.
  4. Challengers (2 parallel): Verify mock uploads, error cases (invalid file, network fail, partial failures).
  5. Forensic Auditor: Verify authentic implementation without hardcoding or facades.
  6. Gate Evaluation: Update `GATE_STATUS.md`.

### Milestone 3: Catalog Pricing Display, Search & Scraper Cleanup (R2, R4)
- **Objective**: Connect AG Grid to `GET /api/v1/catalog/items` and `/catalog/categories`. Display exact manufacturer prices (e.g., Siemens 5SL71057RC = ₹925.00), code, description, unit, category. Implement category filter & text search. Strip away obsolete scraping controls (URL input, "Track Price", scrapers).
- **Iteration Cycle**:
  1. Explorers (3 parallel): Investigate `CatalogGrid.tsx`, AG Grid column definitions, category filter, search debounce, and obsolete scraper code.
  2. Worker: Implement AG Grid catalog data binding, search & filter bar, remove scraper inputs and buttons. Run `npm run build` and `npx vitest run`.
  3. Reviewers (2 parallel): Review code changes, build, and tests.
  4. Challengers (2 parallel): Verify search, category filter, price formatting, absence of scrapers.
  5. Forensic Auditor: Verify authentic integration.
  6. Gate Evaluation.

### Milestone 4: Costing Sheet / Quotation Workflow (R3)
- **Objective**: Integrate `/api/v1/costing-sheets` into spreadsheet interface. Support quotation creation, item selection from catalog, quantity/discount editing with live reactive totals (Line Net, List Total, Net Total, Grand Total) and synchronized backend persistence.
- **Iteration Cycle**:
  1. Explorers (3 parallel): Investigate `costingApi.ts`, `CostingSheetView.tsx`, reactive calculations, sheet line management.
  2. Worker: Implement interactive quotation spreadsheet, reactive calculations, quotation selector/creator, and backend synchronization. Run `npm run build` and `npx vitest run`.
  3. Reviewers (2 parallel): Review quotation spreadsheet, calculations against backend, build/test.
  4. Challengers (2 parallel): Verify calculation precision, CRUD persistence, edge cases.
  5. Forensic Auditor: Verify authentic costing sheet logic.
  6. Gate Evaluation.

### Milestone 5: Full Verification & Quality Gates
- **Objective**: Execute full test suites (`pytest -q`, `npx vitest run`, `npm run build`). Verify Tier 1-4 tests, run adversarial verification, produce final acceptance report.
- **Iteration Cycle**:
  1. Worker / Verifier: Run all test suites and report comprehensive results.
  2. Reviewers & Auditors: Verify 100% pass and no integrity issues.
  3. Final victory report to user.
