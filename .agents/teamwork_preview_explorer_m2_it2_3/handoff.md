# Handoff Report: Explorer 3 — Milestone 2 (Catalog PDF Upload Integration) Iteration 2

## 1. Observation

### 1.1 Evaluated Files & Locations
- **`frontend/src/services/catalogApi.ts`** (lines 111–221): `uploadCatalogPdf` implementation using `XMLHttpRequest` and `AbortSignal`.
- **`frontend/src/tests/catalogApi.test.ts`** (lines 302–331): Existing test case for `AbortSignal` cancellation.
- **`frontend/src/tests/catalogUploadIntegration.test.tsx`** (lines 117–191): `CatalogUpload` component & mock upload integration tests.
- **`frontend/tsconfig.app.json`** (lines 19–24): `"erasableSyntaxOnly": true`, `"noUnusedLocals": true`.
- **`.agents/orchestrator_2/GATE_STATUS.md`**: Gate failure record citing Reviewer 2 findings.
- **`.agents/teamwork_preview_reviewer_m2_2/handoff.md`** (Finding 3): AbortSignal listener leak challenge.

### 1.2 Direct Code Observations

#### A. In `frontend/src/services/catalogApi.ts`:
Lines 120–129 currently register an anonymous arrow function callback directly to `signal.addEventListener`:
```ts
120:    // AbortSignal handling
121:    if (signal) {
122:      if (signal.aborted) {
123:        return reject(new DOMException("Upload aborted", "AbortError"));
124:      }
125:      signal.addEventListener("abort", () => {
126:        xhr.abort();
127:        reject(new DOMException("Upload aborted", "AbortError"));
128:      });
129:    }
```
In the completion and error handlers:
- **`xhr.onload`** (lines 157–194): Resolves HTTP 2xx or rejects HTTP 4xx/5xx, but never calls `removeEventListener` on `signal`.
- **`xhr.onerror`** (lines 197–204): Rejects with `CatalogApiError("Network error...", 0)`, but never calls `removeEventListener` on `signal`.
- **`xhr.ontimeout`** (lines 207–214): Rejects with `CatalogApiError("Upload request timed out...", 408)`, but never calls `removeEventListener` on `signal`.

#### B. In `frontend/src/tests/catalogApi.test.ts`:
Lines 302–331 contain the only test involving `AbortSignal`:
```ts
302:    it("supports AbortSignal cancellation", async () => {
303:      const validFile = new File(["%PDF-1.4 dummy"], "test.pdf", {
304:        type: "application/pdf",
305:      });
306:      const controller = new AbortController();
307:
308:      const fakeXHR = {
309:        open: vi.fn(),
310:        abort: vi.fn(),
311:        send: vi.fn(function () {
312:          // Trigger abort during flight
313:          controller.abort();
314:        }),
315:        upload: { addEventListener: vi.fn() },
316:        addEventListener: vi.fn(),
317:        status: 0,
318:        onload: vi.fn(),
319:        onerror: vi.fn(),
320:        ontimeout: vi.fn(),
321:        timeout: 0,
322:      };
323:
324:      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));
325:
326:      await expect(
327:        uploadCatalogPdf(validFile, { signal: controller.signal }),
328:      ).rejects.toThrow("Upload aborted");
329:      expect(fakeXHR.abort).toHaveBeenCalled();
330:    });
```
This test asserts that `controller.abort()` aborts the XHR and rejects the promise, but does not assert whether the listener was cleaned up on resolution, error, timeout, or abort.

#### C. In `frontend/src/tests/catalogUploadIntegration.test.tsx`:
`uploadCatalogPdf` is mocked via `vi.spyOn(catalogApi, "uploadCatalogPdf")`. No tests in this file assert or depend directly on internal `AbortSignal` listener binding.

---

## 2. Logic Chain

1. **Root Cause of the Leak**:
   - In JavaScript/TypeScript, `signal` is passed in from an external caller (`options.signal`).
   - When `signal.addEventListener("abort", () => { xhr.abort(); reject(...); })` is invoked with an anonymous arrow function, that function reference is retained in the `AbortSignal`'s internal listener registry.
   - The arrow function retains a closure reference to `xhr`, `reject`, `resolve`, and all surrounding scope variables.
   - Because no reference to the callback is stored, it cannot be unregistered with `removeEventListener`.
   - If the upload completes normally (`onload`) or fails with network/timeout errors (`onerror`/`ontimeout`), the listener remains bound to `signal`.
   - If the consumer keeps the `AbortController`/`AbortSignal` alive (e.g. at the component or application level), the closure and the underlying `XMLHttpRequest` object (with any response buffers) cannot be garbage-collected, creating a cumulative memory leak.
   - Furthermore, if the consumer triggers `controller.abort()` after the upload has already settled, the zombie listener executes `xhr.abort()` on an already-settled request.

2. **Required Cleanup Mechanics**:
   - A named function reference `onAbort` must be defined so it can be passed to both `addEventListener` and `removeEventListener`.
   - A dedicated idempotent cleanup helper `cleanupSignal` must be created:
     ```ts
     let onAbort: (() => void) | undefined;
     const cleanupSignal = () => {
       if (signal && onAbort) {
         signal.removeEventListener("abort", onAbort);
         onAbort = undefined;
       }
     };
     ```
   - When `signal` is aborted in flight, `onAbort` must invoke `cleanupSignal()` before calling `xhr.abort()` and `reject(...)`.
   - In all terminal outcomes of `xhr`:
     - `xhr.onload` (both HTTP 2xx success and HTTP 4xx/5xx error responses) must call `cleanupSignal()`.
     - `xhr.onerror` must call `cleanupSignal()`.
     - `xhr.ontimeout` must call `cleanupSignal()`.
   - Setting `onAbort = undefined` inside `cleanupSignal` guarantees idempotency: subsequent calls (e.g., if `xhr.abort()` were to trigger secondary events in a mock environment) do nothing.

3. **Impact on Test Suite**:
   - The existing test `it("supports AbortSignal cancellation")` will continue to pass without changes because calling `cleanupSignal()` inside `onAbort` does not alter the rejection error or `xhr.abort()` invocation.
   - To prevent regressions, dedicated test cases verifying that `signal.removeEventListener("abort", ...)` is called on `onload` (200), `onload` (400), `onerror`, `ontimeout`, and `abort` must be added to `frontend/src/tests/catalogApi.test.ts`.

---

## 3. Caveats

1. **Mock XMLHttpRequest in Vitest**:
   - In Vitest/jsdom unit tests, `XMLHttpRequest` is mocked via `vi.stubGlobal("XMLHttpRequest", ...)`. Tests verifying listener removal must inspect `vi.spyOn(controller.signal, "removeEventListener")` or `vi.spyOn(controller.signal, "addEventListener")`.
2. **Component Integration (`CatalogUpload.tsx`)**:
   - `CatalogUpload.tsx` currently does not pass an `AbortSignal` into `uploadCatalogPdf`. If the implementer introduces an in-flight "Cancel" button (Reviewer 2 Finding 4), `CatalogUpload.tsx` will instantiate an `AbortController` and pass `controller.signal`. If that feature is deferred, the API client will still be fully hardened and compliant for any caller passing a signal.
3. **No Other Areas in `catalogApi.ts` Affected**:
   - `getCatalogImportStatus`, `getCatalogItems`, and `getCatalogCategories` utilize native `fetch()`, which natively handles `AbortSignal` cleanup upon completion without manual event listener management.

---

## 4. Conclusion & Concrete Recommendations

### 4.1 Proposed Implementation for `frontend/src/services/catalogApi.ts`

Replace lines 120–215 with the following exact code:

```ts
    // AbortSignal listener & cleanup definition
    let onAbort: (() => void) | undefined;
    const cleanupSignal = () => {
      if (signal && onAbort) {
        signal.removeEventListener("abort", onAbort);
        onAbort = undefined;
      }
    };

    // AbortSignal handling
    if (signal) {
      if (signal.aborted) {
        return reject(new DOMException("Upload aborted", "AbortError"));
      }
      onAbort = () => {
        cleanupSignal();
        xhr.abort();
        reject(new DOMException("Upload aborted", "AbortError"));
      };
      signal.addEventListener("abort", onAbort);
    }

    // Real-time upload progress tracking
    if (xhr.upload) {
      const handleProgress = (event: ProgressEvent) => {
        if (event.lengthComputable && event.total > 0) {
          const percent = Math.min(
            100,
            Math.max(0, Math.round((event.loaded / event.total) * 100)),
          );
          const progressInfo: UploadProgressInfo = {
            loaded: event.loaded,
            total: event.total,
            percent,
          };
          onProgressCallback?.(progressInfo);
          legacyOnProgress?.(percent);
        }
      };

      if (typeof xhr.upload.addEventListener === "function") {
        xhr.upload.addEventListener("progress", handleProgress);
      } else {
        xhr.upload.onprogress = handleProgress;
      }
    }

    // Response completion handler
    xhr.onload = () => {
      cleanupSignal();
      let body: any = xhr.response;
      if (typeof body === "string") {
        try {
          body = JSON.parse(body);
        } catch {
          // keep as string
        }
      } else if (!body && xhr.responseText) {
        try {
          body = JSON.parse(xhr.responseText);
        } catch {
          body = xhr.responseText;
        }
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as CatalogUploadResponse);
      } else {
        let errorDetail: string;
        if (body && typeof body === "object" && "detail" in body) {
          if (typeof body.detail === "string") {
            errorDetail = body.detail;
          } else if (Array.isArray(body.detail)) {
            errorDetail = body.detail
              .map((e: any) => e.msg || JSON.stringify(e))
              .join(", ");
          } else {
            errorDetail = JSON.stringify(body.detail);
          }
        } else if (typeof body === "string" && body.trim().length > 0) {
          errorDetail = body;
        } else {
          errorDetail = xhr.statusText || `Upload failed with HTTP ${xhr.status}`;
        }
        reject(new CatalogApiError(errorDetail, xhr.status, body));
      }
    };

    // Network error handler
    xhr.onerror = () => {
      cleanupSignal();
      reject(
        new CatalogApiError(
          "Network error: Failed to reach backend server. Please check your connection.",
          0,
        ),
      );
    };

    // Timeout handler
    xhr.ontimeout = () => {
      cleanupSignal();
      reject(
        new CatalogApiError(
          "Upload request timed out while waiting for server response.",
          408,
        ),
      );
    };
```

### 4.2 Proposed Test Suite Additions for `frontend/src/tests/catalogApi.test.ts`

Add a dedicated `describe("uploadCatalogPdf - AbortSignal lifecycle & cleanup", ...)` block immediately following the existing AbortSignal test:

```ts
  describe("uploadCatalogPdf - AbortSignal lifecycle & cleanup", () => {
    it("removes abort event listener from AbortSignal upon successful upload (HTTP 200)", async () => {
      const validFile = new File(["%PDF-1.4 test"], "test.pdf", {
        type: "application/pdf",
      });
      const controller = new AbortController();
      const addListenerSpy = vi.spyOn(controller.signal, "addEventListener");
      const removeListenerSpy = vi.spyOn(controller.signal, "removeEventListener");

      const mockResponse = {
        id: 1,
        file_name: "test.pdf",
        supplier_name: "Siemens",
        status: "completed",
        total_rows: 10,
        imported_rows: 10,
        failed_rows: 0,
        created_at: "2026-09-08T07:00:00Z",
        completed_at: "2026-09-08T07:00:02Z",
      };

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.status = 200;
          fakeXHR.response = mockResponse;
          fakeXHR.onload();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 200,
        response: mockResponse,
        responseText: JSON.stringify(mockResponse),
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      await uploadCatalogPdf(validFile, { signal: controller.signal });

      expect(addListenerSpy).toHaveBeenCalledWith("abort", expect.any(Function));
      expect(removeListenerSpy).toHaveBeenCalledWith("abort", expect.any(Function));
      const addedHandler = addListenerSpy.mock.calls.find((c) => c[0] === "abort")?.[1];
      expect(removeListenerSpy).toHaveBeenCalledWith("abort", addedHandler);
    });

    it("removes abort event listener upon server HTTP error response (HTTP 400)", async () => {
      const validFile = new File(["%PDF-1.4 test"], "test.pdf", {
        type: "application/pdf",
      });
      const controller = new AbortController();
      const addListenerSpy = vi.spyOn(controller.signal, "addEventListener");
      const removeListenerSpy = vi.spyOn(controller.signal, "removeEventListener");

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.status = 400;
          fakeXHR.response = { detail: "Invalid format" };
          fakeXHR.onload();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 400,
        response: { detail: "Invalid format" },
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      await expect(
        uploadCatalogPdf(validFile, { signal: controller.signal }),
      ).rejects.toThrow("Invalid format");

      expect(removeListenerSpy).toHaveBeenCalledWith("abort", expect.any(Function));
      const addedHandler = addListenerSpy.mock.calls.find((c) => c[0] === "abort")?.[1];
      expect(removeListenerSpy).toHaveBeenCalledWith("abort", addedHandler);
    });

    it("removes abort event listener upon network connection error (onerror)", async () => {
      const validFile = new File(["%PDF-1.4 test"], "test.pdf", {
        type: "application/pdf",
      });
      const controller = new AbortController();
      const addListenerSpy = vi.spyOn(controller.signal, "addEventListener");
      const removeListenerSpy = vi.spyOn(controller.signal, "removeEventListener");

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.onerror();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 0,
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      await expect(
        uploadCatalogPdf(validFile, { signal: controller.signal }),
      ).rejects.toThrow("Network error");

      expect(removeListenerSpy).toHaveBeenCalledWith("abort", expect.any(Function));
      const addedHandler = addListenerSpy.mock.calls.find((c) => c[0] === "abort")?.[1];
      expect(removeListenerSpy).toHaveBeenCalledWith("abort", addedHandler);
    });

    it("removes abort event listener upon request timeout (ontimeout)", async () => {
      const validFile = new File(["%PDF-1.4 test"], "test.pdf", {
        type: "application/pdf",
      });
      const controller = new AbortController();
      const addListenerSpy = vi.spyOn(controller.signal, "addEventListener");
      const removeListenerSpy = vi.spyOn(controller.signal, "removeEventListener");

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.ontimeout();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 0,
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      await expect(
        uploadCatalogPdf(validFile, { signal: controller.signal }),
      ).rejects.toThrow("timed out");

      expect(removeListenerSpy).toHaveBeenCalledWith("abort", expect.any(Function));
      const addedHandler = addListenerSpy.mock.calls.find((c) => c[0] === "abort")?.[1];
      expect(removeListenerSpy).toHaveBeenCalledWith("abort", addedHandler);
    });

    it("removes abort event listener when abort is triggered in flight", async () => {
      const validFile = new File(["%PDF-1.4 test"], "test.pdf", {
        type: "application/pdf",
      });
      const controller = new AbortController();
      const addListenerSpy = vi.spyOn(controller.signal, "addEventListener");
      const removeListenerSpy = vi.spyOn(controller.signal, "removeEventListener");

      const fakeXHR = {
        open: vi.fn(),
        abort: vi.fn(),
        send: vi.fn(function () {
          controller.abort();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 0,
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      await expect(
        uploadCatalogPdf(validFile, { signal: controller.signal }),
      ).rejects.toThrow("Upload aborted");

      expect(fakeXHR.abort).toHaveBeenCalled();
      expect(removeListenerSpy).toHaveBeenCalledWith("abort", expect.any(Function));
      const addedHandler = addListenerSpy.mock.calls.find((c) => c[0] === "abort")?.[1];
      expect(removeListenerSpy).toHaveBeenCalledWith("abort", addedHandler);
    });

    it("does not attach listener or start request if signal is pre-aborted", async () => {
      const validFile = new File(["%PDF-1.4 test"], "test.pdf", {
        type: "application/pdf",
      });
      const controller = new AbortController();
      controller.abort();

      const addListenerSpy = vi.spyOn(controller.signal, "addEventListener");
      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(),
        upload: { addEventListener: vi.fn() },
      };
      vi.stubGlobal("XMLHttpRequest", vi.fn(() => fakeXHR));

      await expect(
        uploadCatalogPdf(validFile, { signal: controller.signal }),
      ).rejects.toThrow("Upload aborted");

      expect(addListenerSpy).not.toHaveBeenCalled();
      expect(fakeXHR.send).not.toHaveBeenCalled();
    });
  });
```

---

## 5. Verification Method

### 5.1 Independent Verification Commands
To be run by the implementer/reviewer:
```powershell
# 1. Typecheck and build frontend
cd frontend
npm run build
# Expected: Exit code 0, no errors under erasableSyntaxOnly: true

# 2. Run Vitest test suite including new AbortSignal tests
npx vitest run src/tests/catalogApi.test.ts
# Expected: All tests pass (including existing 21 tests + 6 new lifecycle tests)

# 3. Run full frontend test suite
npx vitest run
# Expected: 100% pass across catalogApi.test.ts, catalogUploadIntegration.test.tsx, and calculations.test.ts
```

### 5.2 Invalidation Conditions
- If `removeEventListenerSpy` is not called with the identical function reference passed to `addEventListenerSpy`, the cleanup is invalid.
- If calling `uploadCatalogPdf` without a `signal` throws a TypeError or NullReferenceError during `onload`/`onerror`/`ontimeout`, the optional signal guard is broken.
- If pre-flight validation failures or pre-aborted signals call `removeEventListener` on an unattached handler, the guard conditions are invalid.
