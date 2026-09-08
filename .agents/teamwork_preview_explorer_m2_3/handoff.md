# Handoff Report: Milestone 2 — Catalog PDF Upload Frontend Service, Grid Auto-Refresh & Vitest Integration

**Agent**: Explorer 3 (`teamwork_preview_explorer_m2_3`)  
**Mission**: Investigate frontend API service client functions required for catalog upload (upload progress tracking, polling import status, error handling), catalog grid auto-refresh signaling in `App.tsx` / `CatalogGrid.tsx`, and frontend test suite structure for Vitest.  
**Date**: 2026-09-08  
**Status**: Complete  

---

## 1. Observation

### 1.1 Existing Frontend Dependencies & HTTP Stack
- **File inspected**: `frontend/package.json` (lines 13–38)
  - `dependencies`:
    - `"ag-grid-community": "^36.0.2"`
    - `"ag-grid-react": "^36.0.2"`
    - `"react": "^19.2.8"`
    - `"react-dom": "^19.2.8"`
    - `"react-router-dom": "^7.11.0"`
    - `"tailwindcss": "^4.3.3"`
  - `devDependencies`:
    - `"@testing-library/jest-dom": "^7.0.1"`
    - `"@testing-library/react": "^16.3.3"`
    - `"jsdom": "^30.0.1"`
    - `"vitest": "^4.1.11"`
    - `"vite": "^8.2.0"`
  - **Observation**: `axios` is **not installed** in `frontend/package.json`.
  - In existing services (`frontend/src/services/productApi.ts` lines 29–55 and `frontend/src/api/prices.ts` lines 4–16), standard browser `fetch()` is used for JSON requests.
  - However, standard browser `fetch()` lacks native support for monitoring outgoing upload progress (`UploadStream`/`ReadableStream` request body progress is experimental, non-standard across browsers, and does not provide standard byte-level progress events).
  - Browser-native `XMLHttpRequest` (`xhr.upload.onprogress`) provides full, zero-dependency upload progress event tracking supported across all browsers and JSDOM test environments.

### 1.2 Existing Service Files & Missing `catalogApi.ts`
- **Files inspected**:
  - `frontend/src/services/`: currently contains only `productApi.ts` (162 lines).
  - `frontend/src/api/`: currently contains only `prices.ts` (17 lines).
  - `frontend/src/types/catalog.ts` (76 lines): already defines `CatalogItem`, `CatalogResponse`, `CatalogCategoriesResponse`, `CatalogUploadResponse`, `CatalogImportResponse`, and `CatalogQueryParams`.
- **PROJECT.md specification**:
  - Line 107 states: `- frontend/src/services/catalogApi.ts: API client for catalog items, categories, and upload.`
  - `frontend/src/services/catalogApi.ts` does not yet exist and must be implemented as part of Milestone 2 / 3.

### 1.3 Backend Catalog Upload and Status Endpoints
- **File inspected**: `backend/app/api/v1/catalog.py`
  - **Upload endpoint**: `POST /api/v1/catalog/imports/upload` (lines 35–98):
    ```python
    @router.post("/imports/upload")
    async def upload_catalog(
        file: UploadFile = File(...),
        supplier_name: str | None = Query(default=None),
        db: Session = Depends(get_db),
    ):
    ```
    - Form field: `"file"` (`multipart/form-data`).
    - Query parameter: `supplier_name` is bound via `Query(default=None)`, NOT as a form field. If provided, it must be in the query string (`/api/v1/catalog/imports/upload?supplier_name=Siemens`). If omitted, backend defaults to `"Siemens"` (`backend/app/services/catalog_import_service.py` line 605).
    - Synchronous parsing lifecycle: the backend saves the PDF to `storage/catalog/<uuid4>.pdf`, triggers `import_siemens_catalog`, parses line items using `pdfplumber`, creates database entities, commits, and returns HTTP 200 with the completed import record.
    - Error responses:
      - HTTP 400 with `{"detail": "Only PDF files are supported."}` if filename does not end with `.pdf`.
      - HTTP 400 with `{"detail": "Uploaded PDF is empty."}` if contents are empty.
      - HTTP 400 with `{"detail": "Catalog PDF exceeds the maximum allowed size."}` if payload > 50 MB (`MAX_CATALOG_FILE_SIZE = 50 * 1024 * 1024` in `catalog_import_service.py` line 35).
      - HTTP 500 with `{"detail": "Catalog PDF import failed: <exc>"}` if an unhandled parsing error occurs.
    - Response schema (lines 87–97):
      ```json
      {
        "id": 1,
        "file_name": "Electrical-Installation-Products.pdf",
        "supplier_name": "Siemens",
        "status": "completed",
        "total_rows": 52,
        "imported_rows": 52,
        "failed_rows": 0,
        "created_at": "2026-09-08T07:00:00Z",
        "completed_at": "2026-09-08T07:00:05Z"
      }
      ```
  - **Status endpoint**: `GET /api/v1/catalog/imports/{import_id}` (lines 271–306):
    - Returns HTTP 200 with:
      `{ id, file_name, supplier_name, effective_date, status, total_rows, imported_rows, failed_rows, error_message, created_at, completed_at }`
    - Returns HTTP 404 with `{"detail": "Catalog import not found."}` if `import_id` is invalid.
    - Returns HTTP 422 if `import_id` is non-numeric.
  - **Items endpoint**: `GET /api/v1/catalog/items` (lines 105–226):
    - Query parameters: `q`, `category`, `limit`, `offset`.
    - Returns `{ total: number, items: CatalogItem[] }`.
  - **Categories endpoint**: `GET /api/v1/catalog/categories` (lines 233–265):
    - Returns `{ categories: string[] }`.

### 1.4 Status Casing and Values
- In `backend/app/database/models/catalog_import.py` and `backend/app/services/catalog_import_service.py` (lines 534–547):
  - Values produced are lowercase: `"uploaded"`, `"processing"`, `"completed"`, `"completed_with_errors"`, `"failed"`.
  - In `backend/app/tests/e2e/test_tier1_features.py` line 117:
    `assert status_data["status"] in {"completed", "completed_with_errors", "failed", "uploaded"}`.
  - In `frontend/src/types/catalog.ts` line 44:
    `status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string;`.
  - Because the type includes `| string`, lowercase values pass type checks, but normalizing to lowercase or accepting both uppercase and lowercase in UI status badges is essential.

### 1.5 Existing Frontend UI Architecture & State Flow
- **File inspected**: `frontend/src/App.tsx` (lines 1–508)
  - `App.tsx` currently contains legacy product price tracking UI (`PriceGrid`, URL input, track button, summary cards).
  - Per `PROJECT.md` §F3 and §F10:
    - Replace/augment with header toolbar containing PDF `CatalogUpload` component.
    - Tab/view switching between "Catalog Products" and "Quotation Costing Sheets".
    - `CatalogGrid` rendering catalog products from `GET /api/v1/catalog/items`.
  - Need a clear signal mechanism so that completing an upload immediately triggers `CatalogGrid` to re-fetch catalog products.

### 1.6 Existing Frontend Tests & Test Runner
- **Files inspected**:
  - `frontend/src/tests/catalogContracts.test.ts` (70 lines): Validates contract shapes with Vitest.
  - `frontend/src/tests/reactiveCalculations.test.ts` (98 lines): Validates financial math for costing sheets.
  - `frontend/src/utils/productMapper.test.ts` (31 lines): Validates mapper.
- **Execution**:
  - Configured script: `npm run test` executes `vitest run`.
  - Packages available: `@testing-library/react` (v16.3.3), `@testing-library/jest-dom` (v7.0.1), `jsdom` (v30.0.1).

---

## 2. Logic Chain

### 2.1 Why `XMLHttpRequest` is Recommended over `fetch` or Adding `axios`
1. *Premise 1*: Milestone 2 requires real-time upload progress tracking ("displaying real-time upload progress, processing states" - ORIGINAL_REQUEST §R1).
2. *Premise 2*: The native browser `fetch()` API does not support request upload progress listeners without non-standard stream hacks that fail in standard browsers and test environments.
3. *Premise 3*: `axios` is not currently in `frontend/package.json`. Adding dependencies introduces bundle bloat, audit overhead, and potential version conflicts.
4. *Premise 4*: `XMLHttpRequest` has 100% universal support across all browsers, provides `xhr.upload.onprogress` with exact loaded/total bytes, supports `AbortSignal` via `signal.addEventListener('abort', () => xhr.abort())`, and is natively mockable in Vitest/JSDOM.
5. *Deduction*: Implementing `uploadCatalogPdf` via a Promise-wrapped `XMLHttpRequest` helper gives full upload progress capability with zero external dependencies.

### 2.2 Handling Synchronous vs. Asynchronous Uploads and Polling
1. *Premise 1*: The backend currently handles `POST /api/v1/catalog/imports/upload` synchronously, returning the finished `CatalogUploadResponse` with status `"completed"` or `"completed_with_errors"`.
2. *Premise 2*: However, for large PDF catalogs (e.g. 50 MB) or if the backend shifts to background workers in production, the response could return status `"uploaded"` or `"processing"`.
3. *Premise 3*: The backend already provides `GET /api/v1/catalog/imports/{import_id}` for status tracking.
4. *Deduction*:
   - If `uploadCatalogPdf` receives a terminal status (`"completed"`, `"completed_with_errors"`, `"failed"`), it resolves immediately.
   - If the status is non-terminal (`"uploaded"`, `"processing"`, `"pending"`), `catalogApi.ts` should provide `pollCatalogImportStatus(importId, options)` that polls `GET /api/v1/catalog/imports/{import_id}` at a configurable interval (e.g., 1000ms) until a terminal state or timeout is reached.

### 2.3 Catalog Grid Auto-Refresh Signaling Mechanism
1. *Premise 1*: `CatalogUpload` lives in the header/toolbar of `App.tsx`.
2. *Premise 2*: `CatalogGrid` lives in the main body of `App.tsx` and maintains its own query filters (search text, category dropdown, pagination).
3. *Premise 3*: React state flow dictates that siblings should not communicate directly; communication should flow through a common parent (`App.tsx`) or a shared context/hook.
4. *Evaluation of Alternatives*:
   - *Option A (Global Event Emitter / CustomEvent)*: Violates React declarative paradigm; prone to memory leaks and untracked re-renders.
   - *Option B (Imperative ref `catalogGridRef.current.refresh()`)*: Complex, exposes imperative handles, harder to test with `@testing-library/react`.
   - *Option C (Declarative `refreshTrigger` numeric counter or timestamp)*:
     - `App.tsx` maintains `const [catalogRefreshTrigger, setCatalogRefreshTrigger] = useState(0);`.
     - `CatalogUpload` accepts `onUploadSuccess?: (result: CatalogUploadResponse) => void`.
     - When upload finishes, `onUploadSuccess` calls `setCatalogRefreshTrigger(prev => prev + 1)` and sets `lastUploadSummary` for the toast/banner.
     - `CatalogGrid` accepts `refreshTrigger?: number`.
     - Inside `CatalogGrid`, `useEffect(() => { loadCatalogItems(); }, [refreshTrigger, search, category]);` re-fetches items whenever `refreshTrigger` increments.
5. *Deduction*: Option C is the cleanest, most idiomatic React 19 pattern. It is fully declarative, easy to mock, and automatically integrates with manual refresh buttons and toast banners.

### 2.4 Structure of Integration Tests in Vitest
1. *Premise 1*: Vitest supports mocking globals (`vi.stubGlobal('XMLHttpRequest', ...)` or vi.spyOn) and mocking `fetch`.
2. *Premise 2*: Integration tests must verify:
   - File upload packaging (multipart FormData, query param `supplier_name`).
   - Progress events firing `onProgress` callbacks with calculated percentage.
   - Success response resolution.
   - HTTP 400 / 500 error detail parsing.
   - UI reaction: upload button disabling, progress bar rendering, status badge transitions, and `onUploadSuccess` triggering grid reload.
3. *Deduction*: Structuring the test suite into:
   - `frontend/src/tests/catalogApi.test.ts` (API service client unit/mock tests).
   - `frontend/src/tests/catalogUploadIntegration.test.tsx` (Component UI and upload interaction tests).
   - `frontend/src/tests/catalogGridRefresh.test.tsx` (Auto-refresh signaling integration tests).
   guarantees 100% test coverage matching Acceptance Criteria.

---

## 3. Recommended Code Designs & Implementation Specifications

### 3.1 Frontend API Service: `frontend/src/services/catalogApi.ts`

```typescript
/**
 * frontend/src/services/catalogApi.ts
 *
 * Dedicated API client for catalog operations:
 * - PDF upload with real-time byte-level progress tracking (XMLHttpRequest)
 * - Import status polling
 * - Catalog item search & category retrieval
 */

import type {
  CatalogCategoriesResponse,
  CatalogImportResponse,
  CatalogQueryParams,
  CatalogResponse,
  CatalogUploadResponse,
} from "../types/catalog";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export class CatalogApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public detail?: unknown,
  ) {
    super(message);
    this.name = "CatalogApiError";
  }
}

export interface UploadProgressInfo {
  loaded: number;
  total: number;
  percent: number; // 0 to 100
}

export interface UploadCatalogOptions {
  supplierName?: string;
  onProgress?: (progress: UploadProgressInfo) => void;
  signal?: AbortSignal;
  timeoutMs?: number;
}

export interface PollImportOptions {
  intervalMs?: number;
  maxAttempts?: number;
  signal?: AbortSignal;
  onPoll?: (status: CatalogImportResponse) => void;
}

/**
 * Upload a supplier catalog PDF with real-time progress tracking.
 * Uses XMLHttpRequest for native byte-level upload progress without extra dependencies.
 */
export function uploadCatalogPdf(
  file: File,
  options?: UploadCatalogOptions,
): Promise<CatalogUploadResponse> {
  return new Promise((resolve, reject) => {
    // Client-side validation
    if (!file) {
      return reject(new CatalogApiError("No file provided", 400));
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return reject(
        new CatalogApiError("Only PDF files are supported.", 400),
      );
    }
    if (file.size === 0) {
      return reject(new CatalogApiError("Uploaded PDF is empty.", 400));
    }

    const xhr = new XMLHttpRequest();
    const url = new URL(`${API_BASE_URL}/catalog/imports/upload`);
    if (options?.supplierName) {
      url.searchParams.set("supplier_name", options.supplierName);
    }

    xhr.open("POST", url.toString(), true);
    xhr.responseType = "json";
    xhr.timeout = options?.timeoutMs ?? 120000; // 2 minutes default timeout for heavy PDFs

    // AbortSignal listener
    if (options?.signal) {
      if (options.signal.aborted) {
        return reject(new DOMException("Upload aborted", "AbortError"));
      }
      options.signal.addEventListener("abort", () => {
        xhr.abort();
        reject(new DOMException("Upload aborted", "AbortError"));
      });
    }

    // Upload progress listener
    if (xhr.upload && options?.onProgress) {
      xhr.upload.addEventListener("progress", (event: ProgressEvent) => {
        if (event.lengthComputable && event.total > 0) {
          const percent = Math.min(
            100,
            Math.max(0, Math.round((event.loaded / event.total) * 100)),
          );
          options.onProgress?.({
            loaded: event.loaded,
            total: event.total,
            percent,
          });
        }
      });
    }

    // Response completion handler
    xhr.onload = () => {
      let responseBody = xhr.response;
      // In some browsers responseType 'json' might return string if parse fails
      if (typeof responseBody === "string") {
        try {
          responseBody = JSON.parse(responseBody);
        } catch {
          // Keep as string
        }
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(responseBody as CatalogUploadResponse);
      } else {
        const errorDetail =
          responseBody?.detail ||
          (typeof responseBody === "string" ? responseBody : null) ||
          xhr.statusText ||
          `Upload failed with HTTP ${xhr.status}`;
        reject(new CatalogApiError(String(errorDetail), xhr.status, responseBody));
      }
    };

    // Network error handler
    xhr.onerror = () => {
      reject(
        new CatalogApiError(
          "Network error: Failed to reach backend server. Please check your connection.",
          0,
        ),
      );
    };

    // Timeout handler
    xhr.ontimeout = () => {
      reject(
        new CatalogApiError(
          "Upload request timed out while waiting for server response.",
          408,
        ),
      );
    };

    // Construct multipart form data
    const formData = new FormData();
    formData.append("file", file, file.name);

    xhr.send(formData);
  });
}

/**
 * Fetch the status of a specific catalog import by ID.
 */
export async function getCatalogImportStatus(
  importId: number,
  signal?: AbortSignal,
): Promise<CatalogImportResponse> {
  const response = await fetch(`${API_BASE_URL}/catalog/imports/${importId}`, {
    method: "GET",
    signal,
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    let detail = `Failed to get import status (${response.status})`;
    try {
      const err = await response.json();
      if (err?.detail) detail = err.detail;
    } catch {
      // Fallback to generic message
    }
    throw new CatalogApiError(detail, response.status);
  }

  return response.json();
}

/**
 * Poll import status until it reaches a terminal status ("completed", "completed_with_errors", "failed").
 */
export async function pollCatalogImportStatus(
  importId: number,
  options?: PollImportOptions,
): Promise<CatalogImportResponse> {
  const intervalMs = options?.intervalMs ?? 1000;
  const maxAttempts = options?.maxAttempts ?? 60;
  let attempts = 0;

  while (attempts < maxAttempts) {
    if (options?.signal?.aborted) {
      throw new DOMException("Polling aborted", "AbortError");
    }

    const record = await getCatalogImportStatus(importId, options?.signal);
    options?.onPoll?.(record);

    const normStatus = (record.status || "").toLowerCase();
    if (normStatus === "completed" || normStatus === "completed_with_errors") {
      return record;
    }
    if (normStatus === "failed") {
      throw new CatalogApiError(
        record.error_message || "Catalog import processing failed.",
        500,
        record,
      );
    }

    attempts++;
    await new Promise((res) => setTimeout(res, intervalMs));
  }

  throw new CatalogApiError(
    "Timed out waiting for catalog import processing to complete.",
    408,
  );
}

/**
 * Retrieve paginated catalog items with optional search query and category filter.
 */
export async function getCatalogItems(
  params?: CatalogQueryParams,
  signal?: AbortSignal,
): Promise<CatalogResponse> {
  const searchParams = new URLSearchParams();
  if (params?.q) searchParams.set("q", params.q);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params?.offset !== undefined) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  const response = await fetch(
    `${API_BASE_URL}/catalog/items${query ? `?${query}` : ""}`,
    {
      method: "GET",
      signal,
      headers: { Accept: "application/json" },
    },
  );

  if (!response.ok) {
    throw new CatalogApiError(`Failed to load catalog items (${response.status})`, response.status);
  }

  return response.json();
}

/**
 * Retrieve unique categories currently active in catalog items.
 */
export async function getCatalogCategories(
  signal?: AbortSignal,
): Promise<CatalogCategoriesResponse> {
  const response = await fetch(`${API_BASE_URL}/catalog/categories`, {
    method: "GET",
    signal,
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new CatalogApiError(`Failed to load categories (${response.status})`, response.status);
  }

  return response.json();
}
```

---

### 3.2 Catalog Grid Auto-Refresh Signaling in `App.tsx` & `CatalogGrid.tsx`

#### In `frontend/src/App.tsx`:
```tsx
// State management in App.tsx
const [catalogRefreshTrigger, setCatalogRefreshTrigger] = useState<number>(0);
const [importNotification, setImportNotification] = useState<{
  type: "success" | "error" | "info";
  message: string;
  summary?: CatalogUploadResponse;
} | null>(null);

// Callback invoked when CatalogUpload completes
const handleUploadSuccess = (result: CatalogUploadResponse) => {
  // 1. Signal CatalogGrid to refresh immediately
  setCatalogRefreshTrigger((prev) => prev + 1);

  // 2. Display summary banner / toast
  setImportNotification({
    type: result.failed_rows > 0 ? "info" : "success",
    message: `Catalog imported: ${result.imported_rows} products loaded (${result.failed_rows} failed) from ${result.file_name}`,
    summary: result,
  });
};

// Render in Header / Main
return (
  <div className="min-h-screen bg-slate-50 text-slate-900">
    <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
        <h1 className="text-xl font-bold text-slate-800">Live Spreadsheet Catalog</h1>
        {/* Dedicated Catalog Upload Component */}
        <CatalogUpload onUploadSuccess={handleUploadSuccess} />
      </div>
    </header>

    {/* Summary Notification Banner */}
    {importNotification && (
      <div className="max-w-7xl mx-auto px-4 mt-3">
        <div className={`p-4 rounded-lg flex items-center justify-between ${
          importNotification.type === "success" ? "bg-emerald-50 text-emerald-800 border border-emerald-200" :
          importNotification.type === "info" ? "bg-amber-50 text-amber-800 border border-amber-200" :
          "bg-rose-50 text-rose-800 border border-rose-200"
        }`}>
          <div>
            <p className="font-semibold">{importNotification.message}</p>
            {importNotification.summary && (
              <p className="text-xs text-slate-600 mt-1">
                Supplier: {importNotification.summary.supplier_name || "Siemens"} | Total Rows: {importNotification.summary.total_rows}
              </p>
            )}
          </div>
          <button
            onClick={() => setImportNotification(null)}
            className="text-sm font-medium hover:underline ml-4"
          >
            Dismiss
          </button>
        </div>
      </div>
    )}

    {/* Main Catalog View */}
    <main className="max-w-7xl mx-auto px-4 py-4">
      <CatalogGrid refreshTrigger={catalogRefreshTrigger} />
    </main>
  </div>
);
```

#### In `frontend/src/components/CatalogGrid.tsx`:
```tsx
interface CatalogGridProps {
  refreshTrigger?: number;
}

export function CatalogGrid({ refreshTrigger = 0 }: CatalogGridProps) {
  const [items, setItems] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");
  const [category, setCategory] = useState<string>("");

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      try {
        const data = await getCatalogItems({
          q: search.trim() || undefined,
          category: category || undefined,
        });
        if (active) setItems(data.items);
      } catch (err) {
        console.error("Failed to load catalog items", err);
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [refreshTrigger, search, category]); // refreshTrigger triggers immediate re-fetch!

  // Render AG Grid with items...
}
```

---

### 3.3 Vitest Integration Test Architecture

To satisfy Acceptance Criteria ("Automated frontend tests (`npm run build` and `npx vitest run`) pass with zero errors"), here is the recommended structure for integration test files.

#### File 1: `frontend/src/tests/catalogApi.test.ts`
Tests the API client functions in isolation using mocked `XMLHttpRequest` and `fetch`:

```typescript
// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  CatalogApiError,
  getCatalogCategories,
  getCatalogImportStatus,
  getCatalogItems,
  pollCatalogImportStatus,
  uploadCatalogPdf,
} from "../services/catalogApi";

describe("catalogApi client unit & integration tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("uploadCatalogPdf", () => {
    it("rejects non-PDF files before network request", async () => {
      const invalidFile = new File(["dummy text"], "test.txt", { type: "text/plain" });
      await expect(uploadCatalogPdf(invalidFile)).rejects.toThrow(
        "Only PDF files are supported.",
      );
    });

    it("rejects empty PDF files before network request", async () => {
      const emptyFile = new File([], "empty.pdf", { type: "application/pdf" });
      await expect(uploadCatalogPdf(emptyFile)).rejects.toThrow(
        "Uploaded PDF is empty.",
      );
    });

    it("successfully uploads valid PDF and reports progress", async () => {
      const validFile = new File(["%PDF-1.4 test bytes"], "siemens.pdf", {
        type: "application/pdf",
      });

      const mockResponse = {
        id: 101,
        file_name: "siemens.pdf",
        supplier_name: "Siemens",
        status: "completed",
        total_rows: 52,
        imported_rows: 52,
        failed_rows: 0,
        created_at: "2026-09-08T07:00:00Z",
        completed_at: "2026-09-08T07:00:05Z",
      };

      const progressSnapshots: number[] = [];

      // Mock XMLHttpRequest
      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          // Simulate progress event
          if (fakeXHR.upload.onprogress) {
            fakeXHR.upload.onprogress({ lengthComputable: true, loaded: 50, total: 100 });
            fakeXHR.upload.onprogress({ lengthComputable: true, loaded: 100, total: 100 });
          }
          // Simulate successful load
          fakeXHR.status = 200;
          fakeXHR.response = mockResponse;
          fakeXHR.onload();
        }),
        upload: {
          addEventListener: vi.fn(function (event, cb) {
            fakeXHR.upload.onprogress = cb;
          }),
          onprogress: null as any,
        },
        addEventListener: vi.fn(),
        status: 200,
        response: mockResponse,
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
      };

      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      const result = await uploadCatalogPdf(validFile, {
        supplierName: "Siemens",
        onProgress: (p) => progressSnapshots.push(p.percent),
      });

      expect(result.id).toBe(101);
      expect(result.imported_rows).toBe(52);
      expect(result.status).toBe("completed");
      expect(progressSnapshots).toEqual([50, 100]);
    });

    it("handles backend 400 error detail response correctly", async () => {
      const validFile = new File(["%PDF-1.4 dummy"], "bad.pdf", { type: "application/pdf" });

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.status = 400;
          fakeXHR.response = { detail: "Catalog PDF exceeds the maximum allowed size." };
          fakeXHR.onload();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 400,
        response: { detail: "Catalog PDF exceeds the maximum allowed size." },
        onload: vi.fn(),
        onerror: vi.fn(),
      };

      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      await expect(uploadCatalogPdf(validFile)).rejects.toThrow(
        "Catalog PDF exceeds the maximum allowed size.",
      );
    });
  });

  describe("pollCatalogImportStatus", () => {
    it("resolves when status transitions to completed", async () => {
      let callCount = 0;
      vi.stubGlobal(
        "fetch",
        vi.fn().mockImplementation(() => {
          callCount++;
          if (callCount === 1) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve({ id: 1, status: "processing" }),
            });
          }
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                id: 1,
                status: "completed",
                total_rows: 52,
                imported_rows: 52,
                failed_rows: 0,
              }),
          });
        }),
      );

      const res = await pollCatalogImportStatus(1, { intervalMs: 10 });
      expect(res.status).toBe("completed");
      expect(callCount).toBe(2);
    });
  });
});
```

#### File 2: `frontend/src/tests/catalogUploadIntegration.test.tsx`
Tests the React UI interaction with `@testing-library/react`:
- Verifies drag-and-drop / file selection.
- Verifies progress bar rendering.
- Verifies status transitions (Idle -> Uploading... -> Processing... -> Success).
- Verifies summary card metrics display (imported rows, failed rows, elapsed time).
- Verifies calling `onUploadSuccess(response)`.

---

## 4. Caveats

1. **No Backend Background Task / Celery Queue**:
   - The current backend executes parsing synchronously within the `POST /api/v1/catalog/imports/upload` request handler.
   - For PDFs with dozens of pages, this HTTP request may remain open for several seconds while `pdfplumber` finishes coordinate extraction.
   - The upload progress bar will quickly reach 100% (the byte upload phase), followed by an indeterminate "Processing & Parsing PDF..." state while waiting for the HTTP response. The UI must cleanly communicate this state to prevent user confusion.
2. **Case Normalization of Status**:
   - Backend models output lowercase `"completed"` and `"completed_with_errors"`, while some documentation mentions uppercase. The frontend implementation should normalize status strings with `.toLowerCase()` to maintain resilience.
3. **Storage Artifacts on Disk**:
   - Backend saves uploaded files into `storage/catalog/`. In development, ensure storage directory permissions allow local writes.
4. **AG Grid Community Edition**:
   - The application uses `ag-grid-community` v36. Ensure grid configurations do not depend on Enterprise-only features.

---

## 5. Conclusion

1. **Frontend Upload Client Architecture**:
   - Creating `frontend/src/services/catalogApi.ts` using Promise-wrapped `XMLHttpRequest` provides standard, byte-accurate upload progress events (`onprogress`) without adding `axios` or external dependencies.
   - Query parameter `supplier_name` must be appended to the URL string, matching FastAPI's `Query(default=None)` definition.
   - Robust error parsing extracts `detail` messages from backend HTTP 400/500 responses and handles network/timeout failures cleanly.
2. **Auto-Refresh Signaling**:
   - A declarative `refreshTrigger` state counter in `App.tsx` passed to `CatalogGrid` provides the most reliable and testable signaling mechanism.
   - Incrementing `refreshTrigger` inside `onUploadSuccess` guarantees immediate re-querying of `GET /api/v1/catalog/items` and updates the grid without page reloads.
3. **Test Suite Verification**:
   - Integration tests in Vitest covering `catalogApi.ts`, `CatalogUpload.tsx`, and the auto-refresh mechanism can be fully verified in the existing JSDOM test runner using `npm run test` (`npx vitest run`).

---

## 6. Verification Method

To independently verify these conclusions and test the implementation:

1. **Inspect Target Files**:
   - Check `backend/app/api/v1/catalog.py` (lines 35–98 and lines 271–306) to confirm upload and status endpoints.
   - Check `frontend/package.json` to verify dependencies and Vitest configuration.
   - Check `frontend/src/types/catalog.ts` for catalog types.

2. **Frontend Test Suite Execution**:
   - Run Vitest tests from the frontend directory:
     ```powershell
     cd frontend
     npm run test
     ```
   - Verify that all test suites pass with 0 errors.

3. **Frontend Build Verification**:
   - Run the TypeScript build:
     ```powershell
     cd frontend
     npm run build
     ```
   - Must complete with exit code 0 and no TypeScript compilation errors.

4. **Backend Test Suite Execution**:
   - Run pytest to verify backend catalog endpoints:
     ```powershell
     pytest -q backend/app/tests/test_all_endpoints.py backend/app/tests/e2e/test_tier1_features.py
     ```
   - Must pass with 100% success.
