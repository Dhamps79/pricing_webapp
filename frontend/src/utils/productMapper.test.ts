import { describe, expect, it } from "vitest";
import { productToRow } from "./productMapper";

describe("productToRow", () => {
  it("maps product pricing correctly", () => {
    const result = productToRow({
      id: 1,
      name: "Test Product",
      image_url: null,
      is_active: true,
      brand_id: null,
      category_id: null,
      description: null,
      unit: "pcs",
      current_price: 100,
      previous_price: 120,
      price_change: -20,
      price_change_percent: -16.67,
      currency: "INR",
      availability: "InStock",
      source_url: "https://example.com",
      source_domain: "example.com",
      fetched_at: "2026-09-03T10:00:00Z",
      trend: "down",
    });

    expect(result.price).toBe(100);
    expect(result.previousPrice).toBe(120);
    expect(result.trend).toBe("down");
  });
});