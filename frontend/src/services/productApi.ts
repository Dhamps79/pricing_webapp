import type { Product } from "../types/product";

const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();

    if (typeof body?.detail === "string") {
      return body.detail;
    }

    return JSON.stringify(body);
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {}),
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      await parseError(response),
    );
  }

  return response.json();
}


export async function getProducts(
  params?: {
    q?: string;
    category_id?: number;
    brand_id?: number;
    limit?: number;
    offset?: number;
  },
): Promise<Product[]> {
  const searchParams = new URLSearchParams();

  if (params?.q) {
    searchParams.set("q", params.q);
  }

  if (params?.category_id !== undefined) {
    searchParams.set(
      "category_id",
      String(params.category_id),
    );
  }

  if (params?.brand_id !== undefined) {
    searchParams.set(
      "brand_id",
      String(params.brand_id),
    );
  }

  if (params?.limit !== undefined) {
    searchParams.set(
      "limit",
      String(params.limit),
    );
  }

  if (params?.offset !== undefined) {
    searchParams.set(
      "offset",
      String(params.offset),
    );
  }

  const query = searchParams.toString();

  return request<Product[]>(
    `/products${query ? `?${query}` : ""}`,
  );
}


export async function getProduct(
  productId: number,
): Promise<Product> {
  return request<Product>(
    `/products/${productId}`,
  );
}


export async function refreshProduct(
  productId: number,
): Promise<Product> {
  return request<Product>(
    `/prices/${productId}/refresh`,
    {
      method: "POST",
    },
  );
}


export async function deleteProduct(
  productId: number,
): Promise<void> {
  await request(
    `/products/${productId}`,
    {
      method: "DELETE",
    },
  );
}