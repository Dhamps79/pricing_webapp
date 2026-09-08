import { describe, expect, it } from "vitest";

/**
 * Pure calculation functions matching backend costing_service.py math:
 * - line_list_total = round(list_price * quantity, 2)
 * - line_net_total = round(sell_price * (1 - discount_percent / 100) * quantity, 2)
 * - sheet_list_total = round(sum(lines.line_list_total), 2)
 * - sheet_net_total = round(sum(lines.line_net_total), 2)
 * - grand_total = round(sheet_net_total * (1 - sheet_discount_percent / 100), 2)
 */

export function calculateLineListTotal(listPrice: number, quantity: number): number {
  return Math.round(listPrice * quantity * 100) / 100;
}

export function calculateLineNetTotal(sellPrice: number, quantity: number, discountPercent: number): number {
  const discountMultiplier = 1 - discountPercent / 100;
  const unitNet = sellPrice * discountMultiplier;
  return Math.round(unitNet * quantity * 100) / 100;
}

export function calculateSheetTotals(
  lines: Array<{ listPrice: number; sellPrice: number; quantity: number; discountPercent: number }>,
  sheetDiscountPercent: number = 0
) {
  let listTotal = 0;
  let netTotal = 0;

  for (const line of lines) {
    listTotal += calculateLineListTotal(line.listPrice, line.quantity);
    netTotal += calculateLineNetTotal(line.sellPrice, line.quantity, line.discountPercent);
  }

  listTotal = Math.round(listTotal * 100) / 100;
  netTotal = Math.round(netTotal * 100) / 100;

  const sheetDiscountMultiplier = 1 - sheetDiscountPercent / 100;
  const grandTotal = Math.round(netTotal * sheetDiscountMultiplier * 100) / 100;

  return {
    listTotal,
    netTotal,
    grandTotal,
  };
}

describe("E2E Frontend Reactive Quotation Math", () => {
  it("computes single line net and list total for Siemens 5SL71057RC @ ₹925.00 with 0% discount", () => {
    const listTotal = calculateLineListTotal(925.0, 5);
    const netTotal = calculateLineNetTotal(925.0, 5, 0.0);
    expect(listTotal).toBe(4625.0);
    expect(netTotal).toBe(4625.0);
  });

  it("computes single line net with 15% discount for 10 units of Siemens 5SL71057RC", () => {
    // 925 * (1 - 0.15) = 786.25 * 10 = 7862.50
    const netTotal = calculateLineNetTotal(925.0, 10, 15.0);
    expect(netTotal).toBe(7862.5);
  });

  it("computes composite sheet totals with multiple lines and sheet-level discount", () => {
    const lines = [
      { listPrice: 2280.0, sellPrice: 2280.0, quantity: 1, discountPercent: 10.0 }, // 2052.00
      { listPrice: 925.0, sellPrice: 925.0, quantity: 8, discountPercent: 15.0 }, // 6290.00
      { listPrice: 925.0, sellPrice: 925.0, quantity: 2, discountPercent: 12.0 }, // 1628.00
    ];
    // Net total: 2052 + 6290 + 1628 = 9970.00
    // Sheet discount: 3.5% => 9970 * 0.965 = 9621.05
    const totals = calculateSheetTotals(lines, 3.5);
    expect(totals.listTotal).toBe(11530.0);
    expect(totals.netTotal).toBe(9970.0);
    expect(totals.grandTotal).toBe(9621.05);
  });

  it("handles boundary condition: 0 quantity", () => {
    const lineNet = calculateLineNetTotal(925.0, 0, 10.0);
    expect(lineNet).toBe(0.0);
  });

  it("handles boundary condition: 100% line discount", () => {
    const lineNet = calculateLineNetTotal(925.0, 5, 100.0);
    expect(lineNet).toBe(0.0);
  });

  it("handles boundary condition: 100% sheet discount", () => {
    const lines = [{ listPrice: 925.0, sellPrice: 925.0, quantity: 10, discountPercent: 0.0 }];
    const totals = calculateSheetTotals(lines, 100.0);
    expect(totals.netTotal).toBe(9250.0);
    expect(totals.grandTotal).toBe(0.0);
  });

  it("handles boundary condition: fractional quantity 2.5", () => {
    // 925 * 2.5 = 2312.50
    const netTotal = calculateLineNetTotal(925.0, 2.5, 0.0);
    expect(netTotal).toBe(2312.5);
  });
});
