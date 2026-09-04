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