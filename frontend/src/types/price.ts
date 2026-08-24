export interface ProductRow {
  id: number;
  name: string;
  imageUrl: string | null;

  price: number;
  currency: string;

  availability: string | null;

  sourceUrl: string;
  sourceDomain: string;

  fetchedAt: string;

  trend: "up" | "down" | "stable";

  // Spreadsheet fields
  quantity: number;
  targetPrice: number | null;
  notes: string;
}