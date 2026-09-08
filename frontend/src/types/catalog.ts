/**
 * Catalog types matching backend /api/v1/catalog endpoints.
 */

export interface CatalogItemAttributes {
  module_width?: string | null;
  rated_current?: string | null;
  poles?: string | null;
  breaking_capacity?: string | null;
  [key: string]: string | number | boolean | null | undefined;
}

export interface CatalogItem {
  id: number;
  product_code: string | null;
  name: string;
  description: string | null;
  unit: string | null;
  image_url: string | null;
  brand_id: number | null;
  brand: string | null;
  category_id: number | null;
  category: string | null;
  price: string | null;
  currency: string;
  attributes?: CatalogItemAttributes;
}

export interface CatalogResponse {
  total: number;
  items: CatalogItem[];
}

export type CatalogItemsResponse = CatalogResponse;

export interface CatalogCategoriesResponse {
  categories: string[];
}

export interface CatalogUploadResponse {
  id: number;
  file_name: string;
  supplier_name: string | null;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | string;
  total_rows: number;
  imported_rows: number;
  failed_rows: number;
  created_at: string;
  completed_at: string | null;
}

export type CatalogImportResponse = CatalogUploadResponse;

export interface CatalogQueryParams {
  q?: string;
  category?: string;
  limit?: number;
  offset?: number;
}

/**
 * Clean flattened model for AG Grid display of catalog items.
 */
export interface CatalogRow {
  id: number;
  productCode: string;
  name: string;
  description: string;
  category: string;
  unit: string;
  moduleWidth: string;
  price: number;
  currency: string;
  attributes: CatalogItemAttributes;
}
