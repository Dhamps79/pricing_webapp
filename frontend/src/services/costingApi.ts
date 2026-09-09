/**
 * frontend/src/services/costingApi.ts
 *
 * API client for costing sheet operations:
 * - CRUD for costing sheets
 * - CRUD for costing sheet lines
 */

import type {
  CostingSheet,
  CostingSheetCreate,
  CostingSheetUpdate,
  CostingLineCreate,
  CostingLineUpdate,
} from "../types/costing";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export class CostingApiError extends Error {
  status?: number;
  detail?: unknown;

  constructor(message: string, status?: number, detail?: unknown) {
    super(message);
    this.name = "CostingApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail)) {
        detail = body.detail
          .map((e: any) => e.msg || JSON.stringify(e))
          .join(", ");
      }
    } catch {
      // fallback
    }
    throw new CostingApiError(detail, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Costing Sheets
// ---------------------------------------------------------------------------

export async function getCostingSheets(
  signal?: AbortSignal,
): Promise<CostingSheet[]> {
  const response = await fetch(`${API_BASE_URL}/costing-sheets`, {
    method: "GET",
    signal,
    headers: { Accept: "application/json" },
  });
  return handleResponse<CostingSheet[]>(response);
}

export async function getCostingSheet(
  sheetId: number,
  signal?: AbortSignal,
): Promise<CostingSheet> {
  const response = await fetch(`${API_BASE_URL}/costing-sheets/${sheetId}`, {
    method: "GET",
    signal,
    headers: { Accept: "application/json" },
  });
  return handleResponse<CostingSheet>(response);
}

export async function createCostingSheet(
  payload: CostingSheetCreate,
  signal?: AbortSignal,
): Promise<CostingSheet> {
  const response = await fetch(`${API_BASE_URL}/costing-sheets`, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<CostingSheet>(response);
}

export async function updateCostingSheet(
  sheetId: number,
  payload: CostingSheetUpdate,
  signal?: AbortSignal,
): Promise<CostingSheet> {
  const response = await fetch(`${API_BASE_URL}/costing-sheets/${sheetId}`, {
    method: "PATCH",
    signal,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<CostingSheet>(response);
}

export async function deleteCostingSheet(
  sheetId: number,
  signal?: AbortSignal,
): Promise<{ message: string; id: number }> {
  const response = await fetch(`${API_BASE_URL}/costing-sheets/${sheetId}`, {
    method: "DELETE",
    signal,
    headers: { Accept: "application/json" },
  });
  return handleResponse<{ message: string; id: number }>(response);
}

// ---------------------------------------------------------------------------
// Costing Lines
// ---------------------------------------------------------------------------

export async function addCostingLine(
  sheetId: number,
  payload: CostingLineCreate,
  signal?: AbortSignal,
): Promise<CostingSheet> {
  const response = await fetch(
    `${API_BASE_URL}/costing-sheets/${sheetId}/lines`,
    {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
  return handleResponse<CostingSheet>(response);
}

export async function updateCostingLine(
  sheetId: number,
  lineId: number,
  payload: CostingLineUpdate,
  signal?: AbortSignal,
): Promise<CostingSheet> {
  const response = await fetch(
    `${API_BASE_URL}/costing-sheets/${sheetId}/lines/${lineId}`,
    {
      method: "PATCH",
      signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    },
  );
  return handleResponse<CostingSheet>(response);
}

export async function deleteCostingLine(
  sheetId: number,
  lineId: number,
  signal?: AbortSignal,
): Promise<CostingSheet> {
  const response = await fetch(
    `${API_BASE_URL}/costing-sheets/${sheetId}/lines/${lineId}`,
    {
      method: "DELETE",
      signal,
      headers: { Accept: "application/json" },
    },
  );
  return handleResponse<CostingSheet>(response);
}

export async function addCostingLinesBatch(
  sheetId: number,
  productIds: number[],
  quantity: number = 1,
  signal?: AbortSignal,
): Promise<CostingSheet> {
  const response = await fetch(
    `${API_BASE_URL}/costing-sheets/${sheetId}/lines/batch`,
    {
      method: "POST",
      signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ product_ids: productIds, quantity }),
    },
  );
  return handleResponse<CostingSheet>(response);
}

export async function exportCostingSheetCsv(
  sheetId: number,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/costing-sheets/${sheetId}/export/csv`,
    {
      method: "GET",
      headers: { Accept: "text/csv" },
    },
  );
  if (!response.ok) {
    throw new CostingApiError(`Export failed (${response.status})`, response.status);
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `costing_sheet_${sheetId}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

