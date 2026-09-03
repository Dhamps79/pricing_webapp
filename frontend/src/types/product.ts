export type PriceTrend = "up" | "down" | "stable";

export interface Product {
  id: number;
  name: string;

  brand_id: number | null;
  category_id: number | null;

  description: string | null;
  unit: string | null;
  image_url: string | null;
  is_active: boolean;

  current_price: number | null;
  previous_price: number | null;
  price_change: number | null;
  price_change_percent: number | null;

  currency: string | null;
  availability: string | null;

  source_url: string | null;
  source_domain: string | null;
  fetched_at: string | null;

  trend: PriceTrend;
}