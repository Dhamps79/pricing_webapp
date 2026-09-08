# Handoff Report: Milestone 2 — Catalog PDF Upload API Contract & Status Tracking

## Executive Summary
This report provides an exhaustive investigation of the backend catalog upload API (`POST /api/v1/catalog/imports/upload`) and status tracking API (`GET /api/v1/catalog/imports/{import_id}`) to guide the implementation of Milestone 2 (Catalog PDF Upload Integration). It documents the exact request encoding, parameter requirements, response schemas, status lifecycle, validation failure modes, elapsed time calculation, and recommended TypeScript contracts for the frontend upload service.

---

## 1. Observation

### 1.1 Backend Upload Endpoint (`POST /api/v1/catalog/imports/upload`)
- **Location**: `backend/app/api/v1/catalog.py` (lines 35–98)
- **Signature**:
  ```python
  @router.post("/imports/upload")
  async def upload_catalog(
      file: UploadFile = File(...),
      supplier_name: str | None = Query(default=None),
      db: Session = Depends(get_db),
  ):
  ```
- **Parameter Analysis**:
  1. `file: UploadFile = File(...)`:
     - Delivered via HTTP `multipart/form-data` with field key `"file"`.
     - File extension validation: `file.filename.lower().endswith(".pdf")`. If false or empty, raises `HTTPException(status_code=400, detail="Only PDF files are supported.")` or `HTTPException(status_code=400, detail="A filename is required.")` (lines 45–55).
     - Payload content validation: `if not contents:` raises `HTTPException(status_code=400, detail="Uploaded PDF is empty.")` (lines 59–63).
     - Maximum file size: checked in `save_catalog_pdf` (`backend/app/services/catalog_import_service.py` line 35: `MAX_CATALOG_FILE_SIZE = 50 * 1024 * 1024`, 50 MB). If exceeded, raises `ValueError("Catalog PDF exceeds the maximum allowed size.")` which maps to HTTP 400.
  2. `supplier_name: str | None = Query(default=None)`:
     - Bound as a **URL query parameter** (e.g. `POST /api/v1/catalog/imports/upload?supplier_name=Siemens`).
     - Defaults to `"Siemens"` if null or omitted (see `catalog_import_service.py` line 605: `supplier_name or "Siemens"`).
     - *Important note*: In FastAPI, `Query(default=None)` binds strictly to URL query string, NOT multipart form body fields. The frontend must supply `supplier_name` as a query parameter when non-default suppliers are used.
- **Execution Lifecycle**:
  - The endpoint is synchronous from the client's perspective: it reads bytes, saves the file to `storage/catalog/<uuid4>.pdf`, creates a `CatalogImport` record, executes `import_siemens_catalog` (extracting text coordinates via `pdfplumber`, parsing MCB line items, creating `Product`, `ProductCode`, `ProductAttribute`, `CatalogPrice`, and `CatalogImportRow` records), commits the transaction, and returns the response immediately upon completion.
  - If a `ValueError` is raised during validation/parsing, it returns HTTP 400 with `{"detail": str(exc)}`.
  - If an unhandled exception occurs, the transaction is rolled back, the uploaded temporary file is unlinked, and it raises HTTP 500 with `{"detail": "Catalog PDF import failed: <exc>"}`.
- **Success Response Structure (HTTP 200)**:
  ```json
  {
    "id": 1,
    "file_name": "Electrical-Installation-Products.pdf",
    "supplier_name": "Siemens",
    "status": "completed",
    "total_rows": 52,
    "imported_rows": 52,
    "failed_rows": 0,
    "created_at": "2026-09-08T07:00:00.123456",
    "completed_at": "2026-09-08T07:00:05.654321"
  }
  ```

### 1.2 Status Tracking Endpoint (`GET /api/v1/catalog/imports/{import_id}`)
- **Location**: `backend/app/api/v1/catalog.py` (lines 271–306)
- **Signature**:
  ```python
  @router.get("/imports/{import_id}")
  def get_catalog_import_status(
      import_id: int,
      db: Session = Depends(get_db),
  ):
  ```
- **Error Codes**:
  - `HTTP 404 Not Found` with `{"detail": "Catalog import not found."}` if `import_id` does not exist in the database (e.g. `import_id <= 0` or non-existent ID). Verified in `backend/app/tests/e2e/test_tier2_boundaries.py` lines 78–86 (`test_b2_get_status_negative_id`, `test_b2_get_status_zero_id`).
  - `HTTP 422 Unprocessable Entity` with standard FastAPI validation error if `import_id` is a non-integer string (e.g., `/api/v1/catalog/imports/invalid-string-id`). Verified in `backend/app/tests/e2e/test_tier2_boundaries.py` line 88 (`test_b2_get_status_non_numeric_id`).
- **Success Response Structure (HTTP 200)**:
  ```json
  {
    "id": 1,
    "file_name": "Electrical-Installation-Products.pdf",
    "supplier_name": "Siemens",
    "effective_date": null,
    "status": "completed",
    "total_rows": 52,
    "imported_rows": 52,
    "failed_rows": 0,
    "error_message": null,
    "created_at": "2026-09-08T07:00:00.123456",
    "completed_at": "2026-09-08T07:00:05.654321"
  }
  ```
- **Listing Endpoint**: Note that there is **NO** `GET /api/v1/catalog/imports` (collection list) endpoint in `catalog.py`. Status tracking is strictly by ID: `GET /api/v1/catalog/imports/{import_id}`.

### 1.3 Status Lifecycle & Casing Discrepancy
- **Database Model**: `backend/app/database/models/catalog_import.py`:
  - `status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")`
- **Service Transitions (`catalog_import_service.py`)**:
  - Line 607: Initially set to `"uploaded"`
  - Line 468: Set to `"processing"` when parser begins
  - Line 536: Set to `"completed"` when parsing finishes and `failed_count == 0`
  - Line 534: Set to `"completed_with_errors"` when parsing finishes and `failed_count > 0`
  - Line 545: Set to `"failed"` if an unhandled parsing exception occurs
- **Test Assertion Verification**:
  - `backend/app/tests/e2e/test_tier1_features.py` line 117:
    `assert status_data["status"] in {"completed", "completed_with_errors", "failed", "uploaded"}`
- **Discrepancy Note**:
  - `PROJECT.md` line 77 displays `"status": "COMPLETED"` (uppercase) in an illustrative example.
  - However, the actual database model, service logic, and E2E test suite strictly produce and verify **lowercase** strings: `"uploaded"`, `"processing"`, `"completed"`, `"completed_with_errors"`, `"failed"`.
  - In `frontend/src/types/catalog.ts` line 44, `status` was typed as `"PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string`. Frontend code must handle lowercase strings (and case-insensitively normalize them).

### 1.4 Auto-Refresh and Read Endpoints (`F3` & Acceptance Criteria)
- Verified in `backend/app/tests/e2e/test_tier1_features.py` lines 154–207 (`test_f3_catalog_readable_before_and_after_upload`):
  - After upload succeeds, the imported products and updated categories are immediately accessible at:
    - `GET /api/v1/catalog/items` (returns `{ total: number, items: CatalogItem[] }`)
    - `GET /api/v1/catalog/categories` (returns `{ categories: string[] }`)
  - The frontend must auto-refresh these queries immediately upon upload completion.

---

## 2. Logic Chain

1. **Parameter Binding Logic**:
   - `upload_catalog` declares `file: UploadFile = File(...)` and `supplier_name: str | None = Query(default=None)`.
   - In FastAPI, parameters marked `Query()` are parsed from query string parameters in `request.url.query`.
   - Therefore, a multipart request submitting `{ supplier_name: "Siemens" }` as a form field will NOT bind `supplier_name`. The client must encode `supplier_name` into the query string: `/api/v1/catalog/imports/upload?supplier_name=...`.
2. **Synchronous vs. Asynchronous Status Semantics**:
   - The backend currently executes the PDF parsing pipeline within the `upload_catalog` request before sending the HTTP response.
   - When the HTTP 200 response is received by the client, the status is already a terminal state (`"completed"` or `"completed_with_errors"`).
   - However, HTTP file transmission itself takes real time (uploading 5–50MB), and backend coordinate clustering takes 1–5 seconds.
   - Therefore, real-time feedback requires:
     a) Client-side byte transfer progress (0% to 100% upload progress via `XMLHttpRequest.upload.onprogress`), followed by
     b) A "Processing catalog items..." indeterminate indicator while waiting for the HTTP response, followed by
     c) Terminal status display ("Imported 52 rows, 0 failed") and timer freezing.
3. **Elapsed Time Calculation**:
   - The response provides `created_at` and `completed_at` as ISO-8601 UTC strings.
   - Server-side duration = `(new Date(completed_at).getTime() - new Date(created_at).getTime()) / 1000` seconds.
   - Client-side duration = active elapsed timer measuring from the instant the user hits "Upload" until the response or error resolves: `((Date.now() - startTime) / 1000).toFixed(1) + "s"`.
   - Displaying the client-side elapsed time provides live ticking feedback during upload/processing, and can be reconciled with backend timestamps upon completion.
4. **Error Handling Logic**:
   - Frontend must catch network errors (e.g. offline, timeout) and HTTP error responses (400, 422, 500).
   - FastAPI returns errors in two formats:
     - Simple string detail: `{ "detail": "A filename is required." }` (HTTP 400, 404, 500)
     - Array of validation errors: `{ "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }` (HTTP 422)
   - The error parser must cleanly extract a human-readable message regardless of whether `detail` is a string or array.

---

## 3. Caveats

1. **Non-PDF and Size Boundaries**:
   - The backend strictly rejects files lacking `.pdf` suffix with 400, empty files with 400, and files exceeding 50 MB with 400.
   - The frontend file selector should restrict `accept=".pdf"` and perform pre-flight checks (file size <= 50MB, non-empty) to provide instantaneous feedback without unnecessary network roundtrips.
2. **No Collection Endpoint**:
   - There is no endpoint to list historical catalog imports (`GET /api/v1/catalog/imports` returns 404/405). Only single-record status by ID (`GET /api/v1/catalog/imports/{id}`) is implemented.
3. **Browser Progress Event Support**:
   - Native `fetch()` does not expose an upload progress event for request bodies. Genuine progress percentages (e.g., 25%, 50%, 75%) require `XMLHttpRequest` (`xhr.upload.onprogress`). If `fetch()` is used, progress must be simulated or limited to binary states (Uploading -> Processing -> Completed).

---

## 4. Conclusion & Recommendations

### 4.1 Recommended TypeScript Interfaces
The existing `frontend/src/types/catalog.ts` should be refined to support both upload and import status contracts:

```typescript
/**
 * Import status enum representing all possible states in backend CatalogImport.
 */
export type CatalogImportStatus =
  | "uploaded"
  | "processing"
  | "completed"
  | "completed_with_errors"
  | "failed"
  | string;

/**
 * Payload returned by POST /api/v1/catalog/imports/upload
 */
export interface CatalogUploadResponse {
  id: number;
  file_name: string;
  supplier_name: string | null;
  status: CatalogImportStatus;
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  created_at: string;
  completed_at: string | null;
}

/**
 * Extended payload returned by GET /api/v1/catalog/imports/{import_id}
 */
export interface CatalogImportDetailResponse extends CatalogUploadResponse {
  effective_date: string | null;
  error_message: string | null;
}
```

### 4.2 Recommended Frontend Service Specification (`frontend/src/services/catalogApi.ts`)
Create `frontend/src/services/catalogApi.ts` exposing:

```typescript
import type {
  CatalogCategoriesResponse,
  CatalogImportDetailResponse,
  CatalogQueryParams,
  CatalogResponse,
  CatalogUploadResponse,
} from "../types/catalog";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

/**
 * Upload a catalog PDF with genuine upload progress tracking.
 *
 * @param file The PDF File object selected by the user.
 * @param supplierName Optional supplier name (e.g. "Siemens"); sent as query parameter.
 * @param onProgress Callback receiving upload progress percentage (0 - 100).
 */
export function uploadCatalogPdf(
  file: File,
  supplierName?: string,
  onProgress?: (percent: number) => void,
): Promise<CatalogUploadResponse> {
  return new Promise((resolve, reject) => {
    // Client-side pre-flight validation
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return reject(new Error("Only PDF files are supported."));
    }
    if (file.size === 0) {
      return reject(new Error("Uploaded PDF is empty."));
    }
    if (file.size > 50 * 1024 * 1024) {
      return reject(new Error("Catalog PDF exceeds the maximum allowed size (50 MB)."));
    }

    const xhr = new XMLHttpRequest();
    const query = supplierName ? `?supplier_name=${encodeURIComponent(supplierName)}` : "";
    xhr.open("POST", `${API_BASE_URL}/catalog/imports/upload${query}`);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      try {
        const body = xhr.responseText ? JSON.parse(xhr.responseText) : {};
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as CatalogUploadResponse);
        } else {
          const detail = typeof body.detail === "string"
            ? body.detail
            : Array.isArray(body.detail)
            ? body.detail.map((e: any) => e.msg || JSON.stringify(e)).join(", ")
            : `Upload failed with HTTP ${xhr.status}`;
          reject(new Error(detail));
        }
      } catch {
        reject(new Error(`Upload failed with HTTP ${xhr.status}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Network connection error during catalog upload."));
    };

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}

/**
 * Fetch detailed status of an import by ID.
 */
export async function getCatalogImportStatus(
  importId: number,
): Promise<CatalogImportDetailResponse> {
  const response = await fetch(`${API_BASE_URL}/catalog/imports/${importId}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Failed to fetch import status: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch catalog products for grid display and auto-refresh.
 */
export async function getCatalogItems(
  params?: CatalogQueryParams,
): Promise<CatalogResponse> {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.set("q", params.q);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  const response = await fetch(`${API_BASE_URL}/catalog/items${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(`Failed to load catalog items: ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch category list for dropdown filter.
 */
export async function getCatalogCategories(): Promise<CatalogCategoriesResponse> {
  const response = await fetch(`${API_BASE_URL}/catalog/categories`);
  if (!response.ok) {
    throw new Error(`Failed to load catalog categories: ${response.status}`);
  }
  return response.json();
}
```

### 4.3 Summary of Contract Parameters Table
| Parameter / Endpoint | Transport | Type | Required | Default / Validation |
|---|---|---|---|---|
| `POST /api/v1/catalog/imports/upload` | Multipart Body | `file` (`File`) | Yes | `.pdf` extension, >0 bytes, <=50MB |
| `POST ...?supplier_name=...` | URL Query String | `supplier_name` (`string`) | No | `"Siemens"` fallback in backend |
| `GET /api/v1/catalog/imports/{import_id}` | Path Parameter | `import_id` (`int`) | Yes | Positive integer; 404 if missing, 422 if string |

---

## 5. Verification Method

### 5.1 Backend Verification
Run the backend E2E test suite covering Features 1, 2, and 3:
```powershell
pytest backend/app/tests/e2e/test_tier1_features.py -k "test_f1 or test_f2 or test_f3" -v
```
To verify boundary rejection and error codes:
```powershell
pytest backend/app/tests/e2e/test_tier2_boundaries.py -k "test_b1 or test_b2 or test_b3" -v
```

### 5.2 Frontend Verification
Run the Vitest test suite and TypeScript compiler:
```powershell
npm --prefix frontend run test
npm --prefix frontend run build
```

### 5.3 Invalidation Conditions
- Backend `upload_catalog` changes `supplier_name` from `Query(...)` to `Form(...)`.
- Asynchronous Celery/RQ background processing is introduced that returns `202 Accepted` rather than `200 OK` with terminal status.
