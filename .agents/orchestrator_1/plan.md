# Execution Plan — PDF Catalog Pricing and Costing Sheet Platform

## Objective
Transform Live Spreadsheet into a polished PDF Catalog Pricing & Costing Sheet management platform fulfilling all requirements in `ORIGINAL_REQUEST.md`:
1. R1: Catalog PDF Upload Integration
2. R2: Catalog Pricing Display & Data Retrieval
3. R3: Costing Sheet / Quotation Workflow
4. R4: Polished Modern UI & Vestigial Cleanup
5. Quality Gates: Frontend build & vitest pass, backend pytest passes 100%, E2E coverage.

## Phase 0: Survey (Full Scope Mapping)
- Dispatch 3 parallel Explorers:
  - Explorer 1: Backend Catalog & Costing Sheet APIs, models, endpoints, schemas, test suite.
  - Explorer 2: Frontend Architecture, AG Grid configuration, current state management, components, vestigial web-scraping controls.
  - Explorer 3: Data flow, integration points, existing tests (vitest, pytest), build scripts.
- Synthesize reports into `PROJECT.md` (Feature Inventory, Milestones, Interface Contracts, Code Layout).

## Phase 1: Dual Track Execution
### Track A: E2E Testing Suite
- Design test infrastructure and test cases for Tiers 1-4.
- Publish `TEST_READY.md`.

### Track B: Implementation Milestones
- **Milestone 1**: PDF Upload Integration (R1)
  - Dedicated upload component in header/toolbar.
  - POST to `/api/v1/catalog/imports/upload` with progress, states, summary, error handling, auto-refresh trigger.
- **Milestone 2**: Catalog Pricing Display & Data Retrieval (R2)
  - Connect AG Grid spreadsheet to `GET /api/v1/catalog/items` and `GET /api/v1/catalog/categories`.
  - Display exact manufacturer prices (MRP/LP), product codes, descriptions, units, categories.
  - Category dropdown filter and text search.
- **Milestone 3**: Costing Sheet / Quotation Workflow (R3)
  - Costing sheet UI integration (`/api/v1/costing-sheets`).
  - Create quotes, add catalog items, edit qty and discount %.
  - Reactive automatic calculations (Line Net, List Total, Net Total, Grand Total).
  - Backend persistence.
- **Milestone 4**: UI Polish & Vestigial Cleanup (R4)
  - Remove all leftover web-scraping controls and obsolete UI.
  - Clean visual hierarchy, loading states, toasts/banners for upload events and errors.

## Phase 2: Final Verification & Hardening
- Run 100% E2E tests (Tiers 1-4).
- Adversarial coverage hardening (Tier 5).
- Forensic audit integrity check.
- Verification of frontend build (`npm run build`), vitest (`npx vitest run`), backend pytest (`pytest -q`).

## Phase 3: Final Synthesis & User Report
- Verify all acceptance criteria are met.
- Compile and deliver user report.
