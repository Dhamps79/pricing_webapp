# Detailed Technical Plan: Frontend TypeScript Types & Build Configuration Fix

**Author**: `teamwork_preview_explorer_m1_2`  
**Milestone**: M1 (Part 2: Frontend Types & Build Fix)  
**Date**: 2026-09-08  
**Scope**: Read-only Exploration & Implementation Specification

---

## 1. Problem Summary & Root Cause Analysis

### 1.1 The Missing `ProductRow` Export in `frontend/src/types/price.ts`
When executing `npm run build` (`tsc -b && vite build`), TypeScript compilation fails immediately because `frontend/src/types/price.ts` does not export `ProductRow`:
```
error TS2305: Module '"../types/price"' has no exported member 'ProductRow'.
```
Three critical frontend files depend directly on `ProductRow` imported from `price.ts`:
1. `frontend/src/utils/productMapper.ts` (lines 2 & 7):
   ```typescript
   import type { ProductRow } from "../types/price";
   export function productToRow(product: Product): ProductRow { ... }
   ```
2. `frontend/src/components/PriceGrid.tsx` (lines 4, 8, 11, 29, 183):
   ```typescript
   import type { ProductRow } from "../types/price";
   interface PriceGridProps {
     rows: ProductRow[];
     onRowsChange: React.Dispatch<React.SetStateAction<ProductRow[]>>;
     ...
   }
   const columnDefs = useMemo<ColDef<ProductRow>[]>(...);
   <AgGridReact<ProductRow> ... />
   ```
3. `frontend/src/App.tsx` (lines 5, 19, 87):
   ```typescript
   import type { ProductRow } from "./types/price";
   const [rows, setRows] = useState<ProductRow[]>([]);
   const row: ProductRow = { ... };
   ```

### 1.2 Comprehensive Field Audit Across All Usage Sites
An exhaustive line-by-line inspection of all consumer files reveals the required fields, data types, and nullability constraints:

| Field Name | Type | Sources / Usages | Notes / Nullability |
| :--- | :--- | :--- | :--- |
| `id` | `number` | `product.id`, `result.product.id`, `PriceGrid` action callbacks | Mandatory primary key |
| `name` | `string` | `product.name`, `result.product.name`, `PriceGrid` column | Product title / MCB model |
| `imageUrl` | `string \| null` | `product.image_url`, `result.product.image_url` | Nullable URL |
| `price` | `number` | `product.current_price ?? 0`, `Number(result.price.value)` | Numeric unit price formatted in `PriceGrid` |
| `previousPrice` | `number \| null` | `product.previous_price`, `existingRow.price` | Nullable prior price |
| `priceChange` | `number \| null` | `product.price_change`, `price - previousPrice` | Nullable absolute delta |
| `priceChangePercent` | `number \| null` | `product.price_change_percent`, `(priceChange / previousPrice) * 100` | Nullable percent delta |
| `currency` | `string \| null` | `product.currency ?? "INR"`, `result.price.currency` | **Crucial**: Must be `string \| null` because `TrackedPriceResponse.price.currency` is `string \| null` |
| `availability` | `string \| null` | `product.availability`, `result.price.availability` | Stock status string |
| `sourceUrl` | `string \| null` | `product.source_url`, `result.source.url` | Web URL or document reference |
| `sourceDomain` | `string \| null` | `product.source_domain`, `result.source.domain` | Host domain or supplier |
| `fetchedAt` | `string \| null` | `product.fetched_at`, `result.price.fetched_at` | ISO timestamp |
| `trend` | `PriceTrend` | `product.trend`, `"stable" \| "up" \| "down"` | `"up" \| "down" \| "stable"` (from `types/product.ts`) |
| `quantity` | `number` | `1`, `item.quantity`, editable column in `PriceGrid` | Spreadsheet quantity multiplier |
| `targetPrice` | `number \| null` | `null`, `item.targetPrice`, editable column in `PriceGrid` | Target price alert threshold |
| `notes` | `string` | `""`, `item.notes`, editable column in `PriceGrid` | User spreadsheet notes |

### 1.3 Missing Test Script in `frontend/package.json`
`frontend/package.json` currently has:
```json
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "oxlint",
    "preview": "vite preview"
  }
```
`vitest` (`^4.1.11`), `@testing-library/react`, and `jsdom` are already present in `devDependencies`, but `"test": "vitest run"` is missing. Adding this allows automated test runners and CI gates to run `npm test`.

---

## 2. Solution Specifications

### 2.1 Type Definition for `ProductRow` in `frontend/src/types/price.ts`
To resolve all compilation errors immediately without modifying `App.tsx`, `PriceGrid.tsx`, or `productMapper.ts`, `frontend/src/types/price.ts` will export `ProductRow` with strict typing and optional catalog extension fields for seamless M2/M3 forward compatibility.

#### Exact Proposed File Content: `frontend/src/types/price.ts`
```typescript
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
```

---

### 2.2 New Types File: `frontend/src/types/catalog.ts`
Design clean TypeScript interfaces reflecting `PROJECT.md` contracts and the backend endpoints:
- `GET /api/v1/catalog/items`
- `GET /api/v1/catalog/categories`
- `POST /api/v1/catalog/imports/upload`

#### Complete Content for `frontend/src/types/catalog.ts`:
```typescript
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

export interface CatalogQueryParams {
  q?: string;
  category?: string;
  limit?: number;
  offset?: number;
}

/**
 * Clean flattened model for AG Grid display of catalog items (Milestone 3).
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
```

---

### 2.3 New Types File: `frontend/src/types/costing.ts`
Design clean TypeScript interfaces reflecting `PROJECT.md` contracts and the backend endpoints:
- `GET /api/v1/costing-sheets`
- `POST /api/v1/costing-sheets`
- `GET /api/v1/costing-sheets/{id}`
- `PATCH /api/v1/costing-sheets/{id}`
- `POST /api/v1/costing-sheets/{id}/lines`
- `PATCH /api/v1/costing-sheets/{id}/lines/{line_id}`
- `DELETE /api/v1/costing-sheets/{id}/lines/{line_id}`

#### Complete Content for `frontend/src/types/costing.ts`:
```typescript
/**
 * Costing sheet types matching backend /api/v1/costing-sheets endpoints.
 */

export interface CostingSheetLine {
  id: number;
  product_id: number;
  sku: string | null;
  name: string;
  category: string | null;
  quantity: string;
  unit: string | null;
  list_price: string;
  sell_price: string;
  discount_percent: string;
  line_list_total: string;
  line_net_total: string;
  notes: string | null;
  sort_order: number;
}

export interface CostingSheet {
  id: number;
  title: string;
  customer_name: string | null;
  notes: string | null;
  discount_percent: string;
  list_total: string;
  net_total: string;
  grand_total: string;
  created_at: string;
  updated_at: string;
  lines: CostingSheetLine[];
}

export interface CostingTotals {
  list_total: number;
  net_total: number;
  grand_total: number;
  total_lines: number;
  total_quantity: number;
  total_discount_amount: number;
}

export interface CostingSheetCreateInput {
  title: string;
  customer_name?: string | null;
  notes?: string | null;
  discount_percent?: number | string;
}

export interface CostingSheetUpdateInput {
  title?: string;
  customer_name?: string | null;
  notes?: string | null;
  discount_percent?: number | string;
}

export interface CostingLineCreateInput {
  product_id: number;
  quantity?: number | string;
  sell_price?: number | string | null;
  discount_percent?: number | string;
  notes?: string | null;
}

export interface CostingLineUpdateInput {
  quantity?: number | string;
  sell_price?: number | string | null;
  discount_percent?: number | string;
  notes?: string | null;
}
```

---

### 2.4 Test Script Addition to `frontend/package.json`

Modify the `"scripts"` block in `frontend/package.json`:
```json
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "oxlint",
    "preview": "vite preview",
    "test": "vitest run"
  },
```

---

## 3. Implementation Instructions for Implementer Agent

### Step 1: Update `frontend/src/types/price.ts`
- Add `import type { PriceTrend } from "./product";` at the top of the file.
- Add the `ProductRow` interface definition at the bottom of `frontend/src/types/price.ts`.

### Step 2: Create `frontend/src/types/catalog.ts`
- Create new file `frontend/src/types/catalog.ts` containing the full interface definitions for `CatalogItemAttributes`, `CatalogItem`, `CatalogResponse`, `CatalogUploadResponse`, `CatalogQueryParams`, and `CatalogRow`.

### Step 3: Create `frontend/src/types/costing.ts`
- Create new file `frontend/src/types/costing.ts` containing the full interface definitions for `CostingSheetLine`, `CostingSheet`, `CostingTotals`, `CostingSheetCreateInput`, `CostingSheetUpdateInput`, `CostingLineCreateInput`, and `CostingLineUpdateInput`.

### Step 4: Update `frontend/package.json`
- Add `"test": "vitest run"` to the `"scripts"` section.

### Step 5: Verification
Run from workspace root:
1. `npm --prefix frontend run build` (runs `tsc -b && vite build`) — must exit with 0 errors.
2. `npm --prefix frontend test` or `npx --prefix frontend vitest run` — must pass all tests (including `productMapper.test.ts`).
