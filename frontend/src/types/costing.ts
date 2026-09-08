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

export interface CostingSheetCreate {
  title: string;
  customer_name?: string | null;
  notes?: string | null;
  discount_percent?: number | string;
}

export type CostingSheetCreateInput = CostingSheetCreate;

export interface CostingSheetUpdate {
  title?: string;
  customer_name?: string | null;
  notes?: string | null;
  discount_percent?: number | string;
}

export type CostingSheetUpdateInput = CostingSheetUpdate;

export interface CostingLineCreate {
  product_id: number;
  quantity?: number | string;
  sell_price?: number | string | null;
  discount_percent?: number | string;
  notes?: string | null;
}

export type CostingLineCreateInput = CostingLineCreate;

export interface CostingLineUpdate {
  quantity?: number | string;
  sell_price?: number | string | null;
  discount_percent?: number | string;
  notes?: string | null;
}

export type CostingLineUpdateInput = CostingLineUpdate;
