import type { PriceTrend } from "./product";

export interface PriceHistoryItem {
  id: number;
  price: string;
  currency: string | null;
  availability: string | null;
  fetched_at: string;
}

export interface PriceHistoryResponse {
  product: {
    id: number;
    name: string;
  };

  history: PriceHistoryItem[];
}

export interface TrackedPriceResponse {
  product: {
    id: number;
    name: string;
    image_url: string | null;
  };

  source: {
    id: number;
    url: string;
    domain: string;
    source_type: string;
  };

  price: {
    id: number;
    value: string;
    currency: string | null;
    availability: string | null;
    fetched_at: string;
  };
}

export interface ProductRow {
  id: number;
  name: string;
  imageUrl: string | null;
  price: number;
  previousPrice: number | null;
  priceChange: number | null;
  priceChangePercent: number | null;
  currency: string | null;
  availability: string | null;
  sourceUrl: string | null;
  sourceDomain: string | null;
  fetchedAt: string | null;
  trend: PriceTrend;
  quantity: number;
  targetPrice: number | null;
  notes: string;

  // Optional forward-compatible catalog fields
  productCode?: string | null;
  category?: string | null;
  unit?: string | null;
  moduleWidth?: string | null;
}