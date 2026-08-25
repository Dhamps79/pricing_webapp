export interface Product {
  id: number;
  name: string;
  image_url: string | null;

  current_price: number | null;
  previous_price: number | null;
  price_change: number | null;
  price_change_percent: number | null;

  currency: string | null;
  availability: string | null;

  source_url: string | null;
  source_domain: string | null;

  fetched_at: string | null;

  trend: "up" | "down" | "stable";
}

const API_BASE_URL = "http://127.0.0.1:8000";

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/products`
  );

  if (!response.ok) {
    throw new Error(
      `Failed to fetch products: ${response.status}`
    );
  }

  return response.json();
}

export async function refreshProduct(
  productId: number,
): Promise<Product> {
  const response = await fetch(
    `http://127.0.0.1:8000/api/v1/prices/${productId}/refresh`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      body || "Failed to refresh product",
    );
  }
  return response.json();
}

export async function deleteProduct(
  productId: number,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/products/${productId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      body || "Failed to delete product",
    );
  }
  return response.json();
}