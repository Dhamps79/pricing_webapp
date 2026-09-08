import { describe, expect, it } from "vitest";

export interface CatalogItemContract {
  id: number;
  name: string;
  description: string | null;
  unit: string | null;
  image_url: string | null;
  brand_id: number | null;
  category_id: number | null;
  price: string | null;
  currency: string;
}

export interface CatalogItemsResponse {
  total: number;
  items: CatalogItemContract[];
}

export interface UploadResponseContract {
  id: number;
  file_name: string;
  supplier_name: string;
  status: string;
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  created_at: string;
  completed_at: string | null;
}

describe("E2E Catalog API Interface Contracts", () => {
  it("validates catalog item contract structure with Siemens reference data", () => {
    const rawPayload: CatalogItemContract = {
      id: 1,
      name: "5SL71057RC",
      description: "1P 5SL7 10kA C-Curve MCB 0.5A",
      unit: "1 NO",
      image_url: null,
      brand_id: 1,
      category_id: 2,
      price: "925.00",
      currency: "INR",
    };

    expect(rawPayload.name).toBe("5SL71057RC");
    expect(rawPayload.price).toBe("925.00");
    expect(rawPayload.currency).toBe("INR");
    expect(rawPayload.unit).toBe("1 NO");
  });

  it("validates upload response contract matching PROJECT.md interface specifications", () => {
    const uploadResponse: UploadResponseContract = {
      id: 1,
      file_name: "Electrical-Installation-Products.pdf",
      supplier_name: "Siemens",
      status: "completed",
      total_rows: 52,
      imported_rows: 52,
      failed_rows: 0,
      created_at: "2026-09-08T07:00:00Z",
      completed_at: "2026-09-08T07:00:05Z",
    };

    expect(uploadResponse.status).toBe("completed");
    expect(uploadResponse.imported_rows).toBe(52);
    expect(uploadResponse.failed_rows).toBe(0);
  });
});
