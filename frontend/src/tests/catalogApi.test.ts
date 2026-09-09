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

  describe("uploadCatalogPdf - client validations", () => {
    it("rejects non-PDF files before network request", async () => {
      const invalidFile = new File(["dummy text"], "test.txt", {
        type: "text/plain",
      });
      await expect(uploadCatalogPdf(invalidFile)).rejects.toThrow(
        "Only PDF files are supported.",
      );
    });

    it("rejects empty PDF files before network request", async () => {
      const emptyFile = new File([], "empty.pdf", {
        type: "application/pdf",
      });
      await expect(uploadCatalogPdf(emptyFile)).rejects.toThrow(
        "Uploaded PDF is empty.",
      );
    });

    it("rejects PDF files exceeding 50 MB", async () => {
      const hugeFile = new File(["dummy"], "huge.pdf", {
        type: "application/pdf",
      });
      Object.defineProperty(hugeFile, "size", {
        value: 51 * 1024 * 1024,
      });
      await expect(uploadCatalogPdf(hugeFile)).rejects.toThrow(
        "Catalog PDF exceeds the maximum allowed size (50 MB).",
      );
    });
  });

  describe("uploadCatalogPdf - network operations", () => {
    it("successfully uploads valid PDF and reports progress updates", async () => {
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

      let capturedUrl = "";
      let capturedMethod = "";
      let capturedFormData: FormData | null = null;

      const fakeXHR = {
        open: vi.fn(function (method: string, url: string) {
          capturedMethod = method;
          capturedUrl = url;
        }),
        send: vi.fn(function (data: FormData) {
          capturedFormData = data;
          if (fakeXHR.upload.onprogress) {
            fakeXHR.upload.onprogress({
              lengthComputable: true,
              loaded: 50,
              total: 100,
            } as ProgressEvent);
            fakeXHR.upload.onprogress({
              lengthComputable: true,
              loaded: 100,
              total: 100,
            } as ProgressEvent);
          }
          fakeXHR.status = 200;
          fakeXHR.response = mockResponse;
          fakeXHR.onload();
        }),
        upload: {
          addEventListener: vi.fn(function (event: string, cb: any) {
            if (event === "progress") fakeXHR.upload.onprogress = cb;
          }),
          onprogress: null as any,
        },
        addEventListener: vi.fn(),
        status: 200,
        response: mockResponse,
        responseText: JSON.stringify(mockResponse),
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", function () { return fakeXHR; });

      const result = await uploadCatalogPdf(validFile, {
        supplierName: "Siemens",
        onProgress: (p) => progressSnapshots.push(p.percent),
      });

      expect(result.id).toBe(101);
      expect(result.imported_rows).toBe(52);
      expect(result.status).toBe("completed");
      expect(progressSnapshots).toEqual([50, 100]);
      expect(capturedMethod).toBe("POST");
      expect(capturedUrl).toContain("/catalog/imports/upload");
      expect(capturedUrl).toContain("supplier_name=Siemens");
      expect(capturedFormData).not.toBeNull();
      const uploadedFile = (capturedFormData as unknown as FormData).get("file") as File;
      expect(uploadedFile.name).toBe(validFile.name);
      expect(uploadedFile.type).toBe(validFile.type);
      expect(uploadedFile.size).toBe(validFile.size);
    });

    it("supports legacy positional arguments (file, supplierName, onProgress)", async () => {
      const validFile = new File(["%PDF-1.4 test"], "catalog.pdf", {
        type: "application/pdf",
      });

      const mockResponse = {
        id: 102,
        file_name: "catalog.pdf",
        supplier_name: "Schneider",
        status: "completed",
        total_rows: 20,
        imported_rows: 20,
        failed_rows: 0,
        created_at: "2026-09-08T07:00:00Z",
        completed_at: "2026-09-08T07:00:02Z",
      };

      const percentList: number[] = [];

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          if (fakeXHR.upload.onprogress) {
            fakeXHR.upload.onprogress({
              lengthComputable: true,
              loaded: 30,
              total: 100,
            } as ProgressEvent);
          }
          fakeXHR.status = 200;
          fakeXHR.response = mockResponse;
          fakeXHR.onload();
        }),
        upload: {
          addEventListener: vi.fn(function (event: string, cb: any) {
            if (event === "progress") fakeXHR.upload.onprogress = cb;
          }),
          onprogress: null as any,
        },
        addEventListener: vi.fn(),
        status: 200,
        response: mockResponse,
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", function () { return fakeXHR; });

      const result = await uploadCatalogPdf(validFile, "Schneider", (percent) => {
        percentList.push(percent);
      });

      expect(result.id).toBe(102);
      expect(percentList).toEqual([30]);
    });

    it("handles backend HTTP 400 string error detail", async () => {
      const validFile = new File(["%PDF-1.4 dummy"], "bad.pdf", {
        type: "application/pdf",
      });

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
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", function () { return fakeXHR; });

      await expect(uploadCatalogPdf(validFile)).rejects.toThrow(
        "Catalog PDF exceeds the maximum allowed size.",
      );
    });

    it("handles backend HTTP 422 array error detail", async () => {
      const validFile = new File(["%PDF-1.4 dummy"], "file.pdf", {
        type: "application/pdf",
      });

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.status = 422;
          fakeXHR.response = {
            detail: [
              { loc: ["query", "supplier_name"], msg: "Invalid format", type: "value_error" },
            ],
          };
          fakeXHR.onload();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 422,
        response: {
          detail: [
            { loc: ["query", "supplier_name"], msg: "Invalid format", type: "value_error" },
          ],
        },
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", function () { return fakeXHR; });

      await expect(uploadCatalogPdf(validFile)).rejects.toThrow("Invalid format");
    });

    it("handles network connection error", async () => {
      const validFile = new File(["%PDF-1.4 dummy"], "test.pdf", {
        type: "application/pdf",
      });

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.onerror();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 0,
        response: null,
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", function () { return fakeXHR; });

      await expect(uploadCatalogPdf(validFile)).rejects.toThrow("Network error");
    });

    it("handles request timeout error", async () => {
      const validFile = new File(["%PDF-1.4 dummy"], "test.pdf", {
        type: "application/pdf",
      });

      const fakeXHR = {
        open: vi.fn(),
        send: vi.fn(function () {
          fakeXHR.ontimeout();
        }),
        upload: { addEventListener: vi.fn() },
        addEventListener: vi.fn(),
        status: 0,
        response: null,
        onload: vi.fn(),
        onerror: vi.fn(),
        ontimeout: vi.fn(),
        timeout: 0,
      };

      vi.stubGlobal("XMLHttpRequest", function () { return fakeXHR; });

      await expect(uploadCatalogPdf(validFile)).rejects.toThrow("timed out");
    });

    it("supports AbortSignal cancellation", async () => {
      const validFile = new File(["%PDF-1.4 dummy"], "test.pdf", {
        type: "application/pdf",
      });
      const controller = new AbortController();

      const fakeXHR = {
        open: vi.fn(),
        abort: vi.fn(),
        send: vi.fn(function () {
          // Trigger abort during flight
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

      vi.stubGlobal("XMLHttpRequest", function () { return fakeXHR; });

      await expect(
        uploadCatalogPdf(validFile, { signal: controller.signal }),
      ).rejects.toThrow("Upload aborted");
      expect(fakeXHR.abort).toHaveBeenCalled();
    });
  });

  describe("getCatalogImportStatus", () => {
    it("fetches import status by ID successfully", async () => {
      const mockDetail = {
        id: 42,
        file_name: "siemens.pdf",
        supplier_name: "Siemens",
        status: "completed",
        total_rows: 52,
        imported_rows: 52,
        failed_rows: 0,
        effective_date: null,
        error_message: null,
        created_at: "2026-09-08T07:00:00Z",
        completed_at: "2026-09-08T07:00:05Z",
      };

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockDetail),
        }),
      );

      const status = await getCatalogImportStatus(42);
      expect(status.id).toBe(42);
      expect(status.status).toBe("completed");
    });

    it("throws CatalogApiError when status fetch fails with 404", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 404,
          json: () => Promise.resolve({ detail: "Catalog import not found." }),
        }),
      );

      await expect(getCatalogImportStatus(999)).rejects.toThrow(
        "Catalog import not found.",
      );
    });
  });

  describe("pollCatalogImportStatus", () => {
    it("polls until status reaches completed", async () => {
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

      const pollSnapshots: string[] = [];
      const res = await pollCatalogImportStatus(1, {
        intervalMs: 10,
        onPoll: (s) => pollSnapshots.push(s.status),
      });

      expect(res.status).toBe("completed");
      expect(callCount).toBe(2);
      expect(pollSnapshots).toEqual(["processing", "completed"]);
    });

    it("throws error when status transitions to failed", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          json: () =>
            Promise.resolve({
              id: 1,
              status: "failed",
              error_message: "Corrupt PDF structure",
            }),
        }),
      );

      await expect(
        pollCatalogImportStatus(1, { intervalMs: 10, maxAttempts: 5 }),
      ).rejects.toThrow("Corrupt PDF structure");
    });

    it("times out if maxAttempts exceeded without reaching terminal state", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve({ id: 1, status: "processing" }),
        }),
      );

      await expect(
        pollCatalogImportStatus(1, { intervalMs: 10, maxAttempts: 2 }),
      ).rejects.toThrow("Timed out waiting for catalog import processing to complete.");
    });
  });

  describe("getCatalogItems and getCatalogCategories", () => {
    it("fetches catalog items with search and category parameters", async () => {
      let requestedUrl = "";
      vi.stubGlobal(
        "fetch",
        vi.fn().mockImplementation((url: string) => {
          requestedUrl = url;
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                total: 1,
                items: [
                  {
                    id: 1,
                    product_code: "5SL71057RC",
                    name: "5SL71057RC",
                    price: "925.00",
                    currency: "INR",
                  },
                ],
              }),
          });
        }),
      );

      const res = await getCatalogItems({ q: "5SL", category: "MCB", limit: 20 });
      expect(res.total).toBe(1);
      expect(res.items[0].product_code).toBe("5SL71057RC");
      expect(requestedUrl).toContain("q=5SL");
      expect(requestedUrl).toContain("category=MCB");
      expect(requestedUrl).toContain("limit=20");
    });

    it("fetches catalog categories list", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve({ categories: ["MCB", "RCCB", "RCBO"] }),
        }),
      );

      const res = await getCatalogCategories();
      expect(res.categories).toEqual(["MCB", "RCCB", "RCBO"]);
    });

    it("throws CatalogApiError when getCatalogItems request fails", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
        }),
      );

      await expect(getCatalogItems()).rejects.toThrow("Failed to load catalog items (500)");
    });

    it("throws CatalogApiError when getCatalogCategories request fails", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 502,
        }),
      );

      await expect(getCatalogCategories()).rejects.toThrow("Failed to load categories (502)");
    });
  });

  describe("CatalogApiError class", () => {
    it("initializes with message, status, and detail properties", () => {
      const err = new CatalogApiError("Custom message", 404, { missing: "id" });
      expect(err.message).toBe("Custom message");
      expect(err.status).toBe(404);
      expect(err.detail).toEqual({ missing: "id" });
      expect(err.name).toBe("CatalogApiError");
    });
  });
});
