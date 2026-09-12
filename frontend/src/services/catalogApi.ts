/**
 * frontend/src/services/catalogApi.ts
 *
 * Dedicated API client for catalog operations:
 * - PDF upload with real-time byte-level progress tracking (XMLHttpRequest)
 * - Import status retrieval and terminal status polling
 * - Catalog item search & category retrieval
 */

import type {
  CatalogCategoriesResponse,
  CatalogQueryParams,
  CatalogResponse,
  CatalogUploadResponse,
} from "../types/catalog";

export type { CatalogImportResponse } from "../types/catalog";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class CatalogApiError extends Error {
  status?: number;
  detail?: unknown;

  constructor(
    message: string,
    status?: number,
    detail?: unknown,
  ) {
    super(message);
    this.name = "CatalogApiError";
    this.status = status;
    this.detail = detail;
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
  onPoll?: (status: CatalogImportDetailResponse) => void;
}

export interface CatalogImportDetailResponse extends CatalogUploadResponse {
  effective_date?: string | null;
  error_message?: string | null;
}

/**
 * Upload a supplier catalog PDF with real-time progress tracking.
 * Uses XMLHttpRequest for native byte-level upload progress without extra dependencies.
 *
 * Supports both options object:
 *   uploadCatalogPdf(file, { supplierName, onProgress, signal, timeoutMs })
 * and positional parameters:
 *   uploadCatalogPdf(file, supplierName, onProgress)
 */
export function uploadCatalogPdf(
  file: File,
  optionsOrSupplierName?: UploadCatalogOptions | string,
  legacyOnProgress?: (percent: number) => void,
): Promise<CatalogUploadResponse> {
  return new Promise((resolve, reject) => {
    // Client-side pre-flight validations
    if (!file) {
      return reject(new CatalogApiError("No file provided", 400));
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return reject(new CatalogApiError("Only PDF files are supported.", 400));
    }
    if (file.size === 0) {
      return reject(new CatalogApiError("Uploaded PDF is empty.", 400));
    }
    const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
    if (file.size > MAX_SIZE) {
      return reject(
        new CatalogApiError("Catalog PDF exceeds the maximum allowed size (50 MB).", 400),
      );
    }

    // Resolve options
    let supplierName: string | undefined;
    let onProgressCallback: ((progress: UploadProgressInfo) => void) | undefined;
    let signal: AbortSignal | undefined;
    let timeoutMs: number | undefined;

    if (typeof optionsOrSupplierName === "string") {
      supplierName = optionsOrSupplierName;
      if (legacyOnProgress) {
        onProgressCallback = (p: UploadProgressInfo) => legacyOnProgress(p.percent);
      }
    } else if (optionsOrSupplierName && typeof optionsOrSupplierName === "object") {
      supplierName = optionsOrSupplierName.supplierName;
      onProgressCallback = optionsOrSupplierName.onProgress;
      signal = optionsOrSupplierName.signal;
      timeoutMs = optionsOrSupplierName.timeoutMs;
      if (legacyOnProgress && !onProgressCallback) {
        onProgressCallback = (p: UploadProgressInfo) => legacyOnProgress(p.percent);
      }
    }

    const xhr = new XMLHttpRequest();
    const endpoint = `${API_BASE_URL}/catalog/imports/upload`;
    const url = new URL(
      endpoint,
      typeof window !== "undefined" ? window.location.origin : "http://localhost:8000",
    );
    if (supplierName) {
      url.searchParams.set("supplier_name", supplierName);
    }

    xhr.open("POST", url.toString(), true);
    xhr.timeout = timeoutMs ?? 120000; // 2 minutes default timeout

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

    const formData = new FormData();
    formData.append("file", file, file.name);

    xhr.send(formData);
  });
}

/**
 * Fetch the detailed status of a specific catalog import by ID.
 */
export async function getCatalogImportStatus(
  importId: number,
  signal?: AbortSignal,
): Promise<CatalogImportDetailResponse> {
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
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail)) {
        detail = body.detail.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
      }
    } catch {
      // Fallback
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
): Promise<CatalogImportDetailResponse> {
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
    if (attempts < maxAttempts) {
      await new Promise((res) => setTimeout(res, intervalMs));
    }
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
    throw new CatalogApiError(
      `Failed to load catalog items (${response.status})`,
      response.status,
    );
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
    throw new CatalogApiError(
      `Failed to load categories (${response.status})`,
      response.status,
    );
  }

  return response.json();
}
