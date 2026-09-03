import type { PriceTrend } from "./product";

export interface ProductRow {
  id: number;
  name: string;

  imageUrl: string | null;

  price: number;
  previousPrice: number | null;

  priceChange: number | null;
  priceChangePercent: number | null;

  currency: string;
  availability: string | null;

  sourceUrl: string | null;
  sourceDomain: string | null;

  fetchedAt: string | null;

  trend: PriceTrend;

  // Spreadsheet fields
  quantity: number;
  targetPrice: number | null;
  notes: string;
}