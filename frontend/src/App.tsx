import { useEffect, useState, useCallback } from "react";
import PriceGrid from "./components/PriceGrid.tsx";
import { CatalogUpload } from "./components/CatalogUpload.tsx";
import { CostingPanel } from "./components/CostingPanel.tsx";
import type { CatalogUploadResponse, CatalogItem, CatalogRow } from "./types/catalog";
import type { CostingSheet } from "./types/costing";
import { getCatalogItems, getCatalogCategories } from "./services/catalogApi";
import { addCostingLine, addCostingLinesBatch, createCostingSheet } from "./services/costingApi";
import { deleteProduct } from "./services/productApi";


/** Map a backend CatalogItem to a flat CatalogRow for the grid. */
function catalogItemToRow(item: CatalogItem): CatalogRow {
  return {
    id: item.id,
    productCode: item.product_code ?? "",
    name: item.name,
    description: item.description ?? "",
    category: item.category ?? "",
    unit: item.unit ?? "Each",
    moduleWidth: item.attributes?.module_width ?? "",
    price: item.price != null ? parseFloat(item.price) : 0,
    currency: item.currency ?? "INR",
    attributes: item.attributes ?? {},
  };
}

function App() {
  // Catalog data state
  const [rows, setRows] = useState<CatalogRow[]>([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);

  // Multi-selection state
  const [selectedRows, setSelectedRows] = useState<CatalogRow[]>([]);
  const [batchActionLoading, setBatchActionLoading] = useState(false);

  // Search & filter
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);

  // Refresh trigger (incremented on upload success)
  const [catalogRefreshTrigger, setCatalogRefreshTrigger] = useState(0);

  // Upload notification
  const [uploadNotification, setUploadNotification] = useState<{
    type: "success" | "info" | "error";
    message: string;
    summary?: CatalogUploadResponse;
  } | null>(null);

  // Costing sheet state
  const [activeSheet, setActiveSheet] = useState<CostingSheet | null>(null);

  // --------------------------------------------------
  // LOAD CATALOG ITEMS
  // --------------------------------------------------
  const loadCatalogItems = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const offset = (currentPage - 1) * pageSize;
      const result = await getCatalogItems({
        q: searchQuery.trim() || undefined,
        category: selectedCategory || undefined,
        limit: pageSize,
        offset: offset,
      });


      setRows(result.items.map(catalogItemToRow));
      setTotalProducts(result.total);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "Failed to load catalog items",
      );
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedCategory, currentPage, pageSize, catalogRefreshTrigger]);

  useEffect(() => {
    loadCatalogItems();
  }, [loadCatalogItems]);


  // --------------------------------------------------
  // LOAD CATEGORIES
  // --------------------------------------------------
  useEffect(() => {
    async function loadCategories() {
      try {
        const result = await getCatalogCategories();
        setCategories(result.categories);
      } catch (err) {
        console.error("Failed to load categories:", err);
      }
    }
    loadCategories();
  }, [catalogRefreshTrigger]);

  // --------------------------------------------------
  // CATALOG UPLOAD SUCCESS
  // --------------------------------------------------
  const handleCatalogUploadSuccess = (response: CatalogUploadResponse) => {
    setCatalogRefreshTrigger((prev) => prev + 1);
    setCurrentPage(1);
    setUploadNotification({
      type: response.failed_rows > 0 ? "info" : "success",
      message: `Successfully imported ${response.imported_rows} products from ${response.file_name} (${response.total_rows} extracted, ${response.failed_rows} failed).`,
      summary: response,
    });
  };

  // --------------------------------------------------
  // ADD TO COSTING SHEET
  // ADD TO COSTING SHEET (Single & Batch)
  // --------------------------------------------------
  const ensureActiveSheet = async (): Promise<CostingSheet> => {
    if (activeSheet) return activeSheet;
    // Auto-create a default sheet if none selected
    const newSheet = await createCostingSheet({
      title: `Quotation - ${new Date().toLocaleDateString("en-IN")}`,
      customer_name: "General Client",
    });
    setActiveSheet(newSheet);
    return newSheet;
  };

  const handleAddToSheet = async (item: CatalogRow) => {
    try {
      setError(null);
      const sheet = await ensureActiveSheet();
      const updated = await addCostingLine(sheet.id, {
        product_id: item.id,
        quantity: 1,
      });
      setActiveSheet(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to add item to sheet",
      );
    }
  };


  const handleBatchAddToSheet = async () => {
    if (selectedRows.length === 0) return;
    try {
      setBatchActionLoading(true);
      setError(null);
      const sheet = await ensureActiveSheet();
      const productIds = selectedRows.map((r) => r.id);
      const updated = await addCostingLinesBatch(sheet.id, productIds, 1);
      setActiveSheet(updated);
      setSelectedRows([]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to batch add items to sheet",
      );
    } finally {
      setBatchActionLoading(false);
    }
  };


  // --------------------------------------------------
  // DELETE PRODUCT
  // --------------------------------------------------
  async function handleDelete(productId: number) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this product?",
    );
    if (!confirmed) return;

    try {
      setError(null);
      await deleteProduct(productId);
      setRows((current) => current.filter((row) => row.id !== productId));
      setTotalProducts((prev) => prev - 1);
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "Unable to delete product",
      );
    }
  }

  // --------------------------------------------------
  // SEARCH (debounced via Enter key)
  // --------------------------------------------------
  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      loadCatalogItems();
    }
  };

  // --------------------------------------------------
  // SUMMARY METRICS
  // --------------------------------------------------
  const totalCatalogValue = rows.reduce(
    (total, row) => total + (row.price || 0),
    0,
  );

  const uniqueCategories = new Set(rows.map((r) => r.category).filter(Boolean));

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------
  return (
    <main className="app">
      {/* HEADER */}
      <header className="app-header">
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span>Live Spreadsheet</span>
            <span
              style={{
                fontSize: "12px",
                background: "#dbeafe",
                color: "#1e40af",
                padding: "2px 8px",
                borderRadius: "12px",
                fontWeight: 600,
              }}
            >
              PDF Catalog &amp; Pricing
            </span>
          </h1>
          <p style={{ margin: 0, color: "#64748b" }}>
            Supplier Catalog Pricing, Direct PDF Ingestion &amp; Quotation
            Costing
          </p>
        </div>
      </header>

      {/* UPLOAD NOTIFICATION BANNER */}
      {uploadNotification && (
        <section
          data-testid="catalog-notification-banner"
          className={`catalog-notification-banner ${
            uploadNotification.type === "success"
              ? "catalog-notification-banner--success"
              : "catalog-notification-banner--info"
          }`}
          style={{
            margin: "0 32px 16px",
            padding: "12px 18px",
            borderRadius: "8px",
            backgroundColor:
              uploadNotification.type === "success" ? "#dcfce7" : "#fef3c7",
            color:
              uploadNotification.type === "success" ? "#166534" : "#92400e",
            border: `1px solid ${
              uploadNotification.type === "success" ? "#86efac" : "#fde68a"
            }`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <strong>
              {uploadNotification.type === "success"
                ? "✓ Catalog Import Success: "
                : "ℹ Catalog Import Notice: "}
            </strong>
            <span>{uploadNotification.message}</span>
            {uploadNotification.summary && (
              <span
                style={{
                  display: "block",
                  fontSize: "12px",
                  color: "#475569",
                  marginTop: "2px",
                }}
              >
                Source: {uploadNotification.summary.supplier_name || "Siemens"}{" "}
                | Total rows: {uploadNotification.summary.total_rows} |
                Imported: {uploadNotification.summary.imported_rows}
              </span>
            )}
          </div>
          <button
            type="button"
            data-testid="dismiss-notification-btn"
            onClick={() => setUploadNotification(null)}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              fontSize: "16px",
              cursor: "pointer",
              fontWeight: "bold",
              marginLeft: "16px",
            }}
            title="Dismiss notification"
          >
            ✕
          </button>
        </section>
      )}


      {/* CATALOG PDF UPLOAD */}
      <section data-testid="catalog-upload-wrapper" style={{ padding: "0 32px" }}>
        <CatalogUpload
          defaultSupplier="Siemens"
          onUploadSuccess={handleCatalogUploadSuccess}
          onUploadError={(err) => setError(err.message)}
        />
      </section>


      {/* SEARCH & FILTER TOOLBAR */}
      <section className="catalog-toolbar">
        <input
          type="text"
          placeholder="Search by product code, name, or description..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setCurrentPage(1);
          }}
          onKeyDown={handleSearchKeyDown}
          className="catalog-search-input"
        />

        <select
          value={selectedCategory}
          onChange={(e) => {
            setSelectedCategory(e.target.value);
            setCurrentPage(1);
          }}
          className="catalog-category-select"
        >
          <option value="">All Categories</option>
          {categories.map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>



        <button
          type="button"
          onClick={loadCatalogItems}
          className="catalog-search-btn"
        >
          🔍 Search
        </button>
      </section>

      {/* SUMMARY STATS */}
      <section className="summary">
        <div className="summary-card">
          <span>Total Products</span>
          <strong>{totalProducts}</strong>
        </div>

        <div className="summary-card">
          <span>Categories</span>
          <strong>{uniqueCategories.size}</strong>
        </div>

        <div className="summary-card">
          <span>Total Catalog Value</span>
          <strong>
            ₹
            {totalCatalogValue.toLocaleString("en-IN", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </strong>
        </div>
      </section>

      {/* ERROR DISPLAY */}
      {error && (
        <div className="error" style={{ margin: "0 32px 16px" }}>
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

      {/* CATALOG PRODUCT GRID */}
      {/* BATCH SELECTION & ACTION BAR */}
      {selectedRows.length > 0 && (
        <section
          style={{
            margin: "0 32px 16px",
            padding: "12px 20px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "8px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600, color: "#1e40af" }}>
              ✓ {selectedRows.length} item{selectedRows.length > 1 ? "s" : ""} selected
            </span>
            <span style={{ fontSize: "13px", color: "#64748b" }}>
              Target: <strong>{activeSheet?.title || "New Quotation Sheet"}</strong>
            </span>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              disabled={batchActionLoading}
              onClick={handleBatchAddToSheet}
              style={{
                background: "#2266dc",
                color: "#fff",
                border: "none",
                borderRadius: "6px",
                padding: "8px 16px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              {batchActionLoading ? "Adding..." : `+ Add ${selectedRows.length} to Costing Sheet`}
            </button>
            <button
              type="button"
              onClick={() => setSelectedRows([])}
              style={{
                background: "transparent",
                color: "#64748b",
                border: "1px solid #cbd5e1",
                borderRadius: "6px",
                padding: "8px 12px",
                cursor: "pointer",
              }}
            >
              Clear Selection
            </button>
          </div>
        </section>
      )}

      {/* CATALOG PRODUCT GRID & SERVER PAGINATION */}
      <section className="grid-container">
        {/* Pagination & Page size bar */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "8px 0 12px",
            fontSize: "13px",
            color: "#475569",
          }}
        >
          <div>
            Showing <strong>{rows.length > 0 ? (currentPage - 1) * pageSize + 1 : 0}</strong> -{" "}
            <strong>{Math.min(currentPage * pageSize, totalProducts)}</strong> of{" "}
            <strong>{totalProducts}</strong> products
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span>Items per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                style={{
                  padding: "4px 8px",
                  borderRadius: "4px",
                  border: "1px solid #cbd5e1",
                  background: "#fff",
                  fontWeight: 500,
                }}
              >
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={250}>250</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </label>

            <div style={{ display: "flex", gap: "6px" }}>
              <button
                type="button"
                disabled={currentPage <= 1 || loading}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                style={{
                  padding: "4px 10px",
                  borderRadius: "4px",
                  border: "1px solid #cbd5e1",
                  background: currentPage <= 1 ? "#f1f5f9" : "#fff",
                  cursor: currentPage <= 1 ? "not-allowed" : "pointer",
                  color: currentPage <= 1 ? "#94a3b8" : "#334155",
                }}
              >
                ◀ Prev
              </button>
              <span style={{ padding: "4px 8px", fontWeight: 600 }}>
                Page {currentPage} of {Math.max(1, Math.ceil(totalProducts / pageSize))}
              </span>
              <button
                type="button"
                disabled={currentPage >= Math.ceil(totalProducts / pageSize) || loading}
                onClick={() => setCurrentPage((prev) => prev + 1)}
                style={{
                  padding: "4px 10px",
                  borderRadius: "4px",
                  border: "1px solid #cbd5e1",
                  background:
                    currentPage >= Math.ceil(totalProducts / pageSize) ? "#f1f5f9" : "#fff",
                  cursor:
                    currentPage >= Math.ceil(totalProducts / pageSize) ? "not-allowed" : "pointer",
                  color:
                    currentPage >= Math.ceil(totalProducts / pageSize) ? "#94a3b8" : "#334155",
                }}
              >
                Next ▶
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div
            style={{
              padding: "48px",
              textAlign: "center",
              color: "#64748b",
              fontSize: "14px",
            }}
          >
            Loading catalog data...
          </div>
        ) : (
          <PriceGrid
            rows={rows}
            onAddToSheet={handleAddToSheet}
            onDelete={handleDelete}
            onSelectionChanged={setSelectedRows}
            pageSize={pageSize}
          />

        )}
      </section>

      {/* COSTING SHEET PANEL */}
      <CostingPanel
        activeSheet={activeSheet}
        onSheetChange={setActiveSheet}
      />

    </main>
  );
}

export default App;