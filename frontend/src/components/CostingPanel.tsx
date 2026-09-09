import { useState, useEffect, useCallback } from "react";
import type { CostingSheet, CostingSheetLine } from "../types/costing";
import {
  getCostingSheets,
  getCostingSheet,
  createCostingSheet,
  updateCostingSheet,
  deleteCostingSheet,
  updateCostingLine,
  deleteCostingLine,
  exportCostingSheetCsv,
} from "../services/costingApi";
import "./CostingPanel.css";


export interface CostingPanelProps {
  /** The currently active sheet (managed by parent). */
  activeSheet: CostingSheet | null;
  /** Called when the active sheet changes (select, create, update, delete). */
  onSheetChange: (sheet: CostingSheet | null) => void;
}

export function CostingPanel({ activeSheet, onSheetChange }: CostingPanelProps) {
  const [sheets, setSheets] = useState<CostingSheet[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newCustomer, setNewCustomer] = useState("");

  // Load sheets list
  const loadSheets = useCallback(async () => {
    try {
      setLoading(true);
      const result = await getCostingSheets();
      setSheets(result);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to load sheets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSheets();
  }, [loadSheets]);

  // Create sheet
  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    try {
      setError(null);
      const sheet = await createCostingSheet({
        title: newTitle.trim(),
        customer_name: newCustomer.trim() || null,
      });
      setSheets((prev) => [...prev, sheet]);
      onSheetChange(sheet);
      setNewTitle("");
      setNewCustomer("");
      setShowCreateForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create sheet");
    }
  };

  // Select sheet
  const handleSelectSheet = async (sheetId: number) => {
    if (sheetId === 0) {
      onSheetChange(null);
      return;
    }
    try {
      setError(null);
      const sheet = await getCostingSheet(sheetId);
      onSheetChange(sheet);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sheet");
    }
  };

  // Delete sheet
  const handleDeleteSheet = async () => {
    if (!activeSheet) return;
    const confirmed = window.confirm(
      `Delete costing sheet "${activeSheet.title}"?`,
    );
    if (!confirmed) return;
    try {
      setError(null);
      await deleteCostingSheet(activeSheet.id);
      setSheets((prev) => prev.filter((s) => s.id !== activeSheet.id));
      onSheetChange(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete sheet");
    }
  };

  // Update sheet discount
  const handleUpdateDiscount = async (discountStr: string) => {
    if (!activeSheet) return;
    const discount = parseFloat(discountStr);
    if (isNaN(discount) || discount < 0 || discount > 100) return;
    try {
      setError(null);
      const updated = await updateCostingSheet(activeSheet.id, {
        discount_percent: discount,
      });
      onSheetChange(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update sheet");
    }
  };

  // Update line
  const handleUpdateLine = async (
    lineId: number,
    field: "quantity" | "sell_price" | "discount_percent",
    value: string,
  ) => {
    if (!activeSheet) return;
    const numVal = parseFloat(value);
    if (isNaN(numVal) || numVal < 0) return;
    try {
      setError(null);
      const updated = await updateCostingLine(activeSheet.id, lineId, {
        [field]: numVal,
      });
      onSheetChange(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update line");
    }
  };

  // Delete line
  const handleDeleteLine = async (lineId: number) => {
    if (!activeSheet) return;
    try {
      setError(null);
      const updated = await deleteCostingLine(activeSheet.id, lineId);
      onSheetChange(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove line");
    }
  };

  const formatCurrency = (val: string | number) => {
    const num = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(num)) return "₹0.00";
    return `₹${num.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="costing-panel">
      {/* Header */}
      <div className="costing-header">
        <div className="costing-header-left">
          <div className="costing-header-title">
            <span className="costing-icon">📋</span>
            Costing Sheet
          </div>

          <select
            className="costing-sheet-select"
            value={activeSheet?.id ?? 0}
            onChange={(e) => handleSelectSheet(Number(e.target.value))}
          >
            <option value={0}>
              {loading ? "Loading..." : "— Select a sheet —"}
            </option>
            {sheets.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
                {s.customer_name ? ` (${s.customer_name})` : ""}
              </option>
            ))}
          </select>
        </div>

        <div className="costing-header-actions">
          {activeSheet && (
            <button
              type="button"
              className="costing-btn costing-btn--outline costing-btn--sm"
              style={{ background: "#f8fafc", borderColor: "#cbd5e1", color: "#334155" }}
              onClick={async () => {
                try {
                  await exportCostingSheetCsv(activeSheet.id);
                } catch (err: any) {
                  setError(err.message || "Export failed");
                }
              }}
              title="Download sheet as CSV file"
            >
              📥 Export CSV
            </button>
          )}
          <button
            type="button"
            className="costing-btn costing-btn--primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            + New Sheet
          </button>
          {activeSheet && (
            <button
              type="button"
              className="costing-btn costing-btn--danger costing-btn--sm"
              onClick={handleDeleteSheet}
            >
              Delete
            </button>
          )}
        </div>
      </div>


      {/* Create Form */}
      {showCreateForm && (
        <div className="costing-create-form">
          <input
            type="text"
            placeholder="Sheet title..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <input
            type="text"
            placeholder="Customer name (optional)"
            value={newCustomer}
            onChange={(e) => setNewCustomer(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button
            type="button"
            className="costing-btn costing-btn--primary"
            onClick={handleCreate}
            disabled={!newTitle.trim()}
          >
            Create
          </button>
          <button
            type="button"
            className="costing-btn costing-btn--ghost"
            onClick={() => setShowCreateForm(false)}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          style={{
            padding: "8px 20px",
            background: "#fee2e2",
            color: "#991b1b",
            fontSize: "13px",
          }}
        >
          {error}
          <button
            type="button"
            onClick={() => setError(null)}
            style={{
              marginLeft: 8,
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontWeight: "bold",
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Active Sheet Content */}
      {activeSheet ? (
        <>
          {/* Info Bar */}
          <div className="costing-info-bar">
            <div className="costing-info-item">
              <label>Customer:</label>
              <span>{activeSheet.customer_name || "—"}</span>
            </div>
            <div className="costing-info-item">
              <label>Sheet Discount (%):</label>
              <input
                type="number"
                className="costing-info-input"
                defaultValue={activeSheet.discount_percent}
                min={0}
                max={100}
                step={0.5}
                onBlur={(e) => handleUpdateDiscount(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    (e.target as HTMLInputElement).blur();
                  }
                }}
              />
            </div>
            <div className="costing-info-item">
              <label>Lines:</label>
              <span>{activeSheet.lines.length}</span>
            </div>
          </div>

          {/* Lines Table */}
          {activeSheet.lines.length > 0 ? (
            <div style={{ overflowX: "auto" }}>
              <table className="costing-lines-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>SKU</th>
                    <th>Product</th>
                    <th className="text-right">List Price</th>
                    <th className="text-right">Qty</th>
                    <th className="text-right">Sell Price</th>
                    <th className="text-right">Disc %</th>
                    <th className="text-right">Line Net</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {activeSheet.lines.map(
                    (line: CostingSheetLine, idx: number) => (
                      <tr key={line.id}>
                        <td style={{ color: "#94a3b8" }}>{idx + 1}</td>
                        <td>
                          <span className="costing-line-sku">
                            {line.sku || "—"}
                          </span>
                        </td>
                        <td>
                          <span className="costing-line-name" title={line.name}>
                            {line.name}
                          </span>
                        </td>
                        <td className="text-right">
                          {formatCurrency(line.list_price)}
                        </td>
                        <td className="text-right">
                          <input
                            type="number"
                            className="line-input"
                            defaultValue={line.quantity}
                            min={1}
                            onBlur={(e) =>
                              handleUpdateLine(
                                line.id,
                                "quantity",
                                e.target.value,
                              )
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                (e.target as HTMLInputElement).blur();
                              }
                            }}
                          />
                        </td>
                        <td className="text-right">
                          <input
                            type="number"
                            className="line-input"
                            defaultValue={line.sell_price}
                            min={0}
                            step={0.01}
                            onBlur={(e) =>
                              handleUpdateLine(
                                line.id,
                                "sell_price",
                                e.target.value,
                              )
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                (e.target as HTMLInputElement).blur();
                              }
                            }}
                          />
                        </td>
                        <td className="text-right">
                          <input
                            type="number"
                            className="line-input"
                            defaultValue={line.discount_percent}
                            min={0}
                            max={100}
                            step={0.5}
                            onBlur={(e) =>
                              handleUpdateLine(
                                line.id,
                                "discount_percent",
                                e.target.value,
                              )
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                (e.target as HTMLInputElement).blur();
                              }
                            }}
                          />
                        </td>
                        <td className="text-right" style={{ fontWeight: 600 }}>
                          {formatCurrency(line.line_net_total)}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="costing-remove-btn"
                            onClick={() => handleDeleteLine(line.id)}
                            title="Remove line"
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="costing-empty">
              <div className="costing-empty-icon">🛒</div>
              No items yet. Use "Add to Sheet" in the catalog grid above to add
              products.
            </div>
          )}

          {/* Totals */}
          <div className="costing-totals">
            <div className="costing-total-card">
              <span className="costing-total-label">List Total</span>
              <span className="costing-total-value">
                {formatCurrency(activeSheet.list_total)}
              </span>
            </div>
            <div className="costing-total-card">
              <span className="costing-total-label">Net Total</span>
              <span className="costing-total-value">
                {formatCurrency(activeSheet.net_total)}
              </span>
            </div>
            <div className="costing-total-card costing-total-card--grand">
              <span className="costing-total-label">Grand Total</span>
              <span className="costing-total-value">
                {formatCurrency(activeSheet.grand_total)}
              </span>
            </div>
          </div>
        </>
      ) : (
        <div className="costing-empty">
          <div className="costing-empty-icon">📊</div>
          Select or create a costing sheet to start building a quotation.
        </div>
      )}
    </div>
  );
}

export default CostingPanel;
