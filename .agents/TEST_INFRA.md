# Test Infrastructure: PDF Catalog Pricing & Costing Sheet Management Platform

## 1. Overview & Architecture
The test infrastructure provides an opaque-box, requirement-driven E2E verification framework spanning backend REST services, database persistence, and frontend reactive calculations across four systematic tiers.

The testing architecture is dual-stack:
- **Backend Test Runner**: Pytest 8.x with `FastAPI TestClient`, `SQLAlchemy`, and custom fixture lifecycle in Python 3.12.
- **Frontend Test Runner**: Vitest 4.x with `jsdom`, `testing-library`, and pure TypeScript financial calculation verification.

---

## 2. Directory Structure

```
live-spreadsheet/
├── backend/
│   └── app/
│       └── tests/
│           ├── __init__.py
│           ├── test_all_endpoints.py            # Legacy endpoint regression suite
│           ├── test_e2e_suite.py                # Aggregated master E2E test runner
│           └── e2e/
│               ├── __init__.py
│               ├── conftest.py                  # Shared fixtures, DB setup, sample PDF generators
│               ├── test_tier1_features.py       # Tier 1: 55+ tests (5+ per feature in isolation)
│               ├── test_tier2_boundaries.py     # Tier 2: 55+ tests (5+ boundary/corner cases per feature)
│               ├── test_tier3_cross_feature.py  # Tier 3: 6 Pairwise integration workflows
│               └── test_tier4_scenarios.py      # Tier 4: 5 Authentic Siemens Betagard real-world quotes
└── frontend/
    └── src/
        └── tests/
            ├── reactiveCalculations.test.ts     # Vitest suite for Line Net, List Total, Grand Total math
            └── catalogContracts.test.ts         # Vitest suite for Catalog & Upload JSON schemas
```

---

## 3. Test Fixtures & Capabilities (`backend/app/tests/e2e/conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `init_test_database` | session (autouse) | Invokes `Base.metadata.create_all(bind=engine)` ensuring all tables exist before test execution. |
| `client` | function | Provides `fastapi.testclient.TestClient(app)` configured with application routes and middleware. |
| `db` | function | Yields a transactional SQLAlchemy `SessionLocal()` with guaranteed teardown cleanup. |
| `test_brand` | function | Retrieves or seeds the canonical "Siemens" manufacturer brand. |
| `test_category` | function | Retrieves or seeds the canonical "MCB" product category. |
| `siemens_5sl71057rc_product` | function | Authoritative reference item: Siemens 5SL71057RC (1P 10kA C-Curve MCB 0.5A) with exact price ₹925.00 and currency INR. |
| `make_valid_pdf_bytes()` | helper | Generates minimal valid PDF header/trailer byte arrays for in-memory upload tests. |
| `get_real_sample_pdf_path()` | helper | Resolves root-level manufacturer catalog `Electrical-Installation-Products-from-A-to-Z-Pricelist-wef-1st-July-2027_compressed.pdf`. |

---

## 4. Execution Commands

### Backend Pytest Suite
```bash
# Run all E2E tiers with summary output
pytest -q backend/app/tests/test_e2e_suite.py

# Run individual tiers
pytest -q backend/app/tests/e2e/test_tier1_features.py
pytest -q backend/app/tests/e2e/test_tier2_boundaries.py
pytest -q backend/app/tests/e2e/test_tier3_cross_feature.py
pytest -q backend/app/tests/e2e/test_tier4_scenarios.py

# Run entire backend test suite
pytest -q
```

### Frontend Vitest Suite
```bash
cd frontend
npx vitest run
```

---

## 5. Authoritative Output Oracles

For all test assertions, expected values are derived from two immutable sources:
1. **Manufacturer PDF Pricelist**:
   - `5SL71057RC` (1P MCB 0.5A) = ₹925.00
   - `5SL72167RC` (2P MCB 16A) = ₹2,280.00
   - `5SL73327RC` (3P MCB 32A) = ₹3,840.00
   - `5SL74637RC` (4P MCB 63A) = ₹5,120.00
2. **PROJECT.md Mathematical Contract**:
   $$\text{Line List Total} = \text{round}(\text{list\_price} \times \text{quantity}, 2)$$
   $$\text{Line Net Total} = \text{round}\left(\text{sell\_price} \times \left(1 - \frac{\text{discount\_percent}}{100}\right) \times \text{quantity}, 2\right)$$
   $$\text{Sheet List Total} = \text{round}\left(\sum \text{Line List Total}, 2\right)$$
   $$\text{Sheet Net Total} = \text{round}\left(\sum \text{Line Net Total}, 2\right)$$
   $$\text{Grand Total} = \text{round}\left(\text{Sheet Net Total} \times \left(1 - \frac{\text{sheet\_discount\_percent}}{100}\right), 2\right)$$
