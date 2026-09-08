import { useEffect, useState } from "react";
import PriceGrid from "./components/PriceGrid.tsx";
import { CatalogUpload } from "./components/CatalogUpload.tsx";
import type { CatalogUploadResponse } from "./types/catalog";
import type { ProductRow } from "./types/price";
import {
  getProducts,
  refreshProduct,
  deleteProduct,
} from "./services/productApi";
import { productToRow } from "./utils/productMapper";

function App() {
  const [rows, setRows] = useState<ProductRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Declarative refresh counter incremented on upload success to auto-refresh data
  const [catalogRefreshTrigger, setCatalogRefreshTrigger] = useState(0);

  // Summary notification banner state
  const [uploadNotification, setUploadNotification] = useState<{
    type: "success" | "info" | "error";
    message: string;
    summary?: CatalogUploadResponse;
  } | null>(null);

  // --------------------------------------------------
  // LOAD PRODUCTS (refreshes when catalogRefreshTrigger changes)
  // --------------------------------------------------
  useEffect(() => {
    async function loadProducts() {
      try {
        setLoading(true);
        setError(null);

        const products = await getProducts();
        setRows(products.map(productToRow));
      } catch (err) {
        console.error(err);
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load products",
        );
      } finally {
        setLoading(false);
      }
    }

    loadProducts();
  }, [catalogRefreshTrigger]);

  // --------------------------------------------------
  // CATALOG UPLOAD SUCCESS HANDLER
  // --------------------------------------------------
  const handleCatalogUploadSuccess = (response: CatalogUploadResponse) => {
    // 1. Increment declarative refresh trigger to auto-refresh products
    setCatalogRefreshTrigger((prev) => prev + 1);

    // 2. Display summary notification banner
    setUploadNotification({
      type: response.failed_rows > 0 ? "info" : "success",
      message: `Successfully imported ${response.imported_rows} products from ${response.file_name} (${response.total_rows} extracted, ${response.failed_rows} failed).`,
      summary: response,
    });
  };

  // --------------------------------------------------
  // REFRESH PRODUCT
  // --------------------------------------------------
  async function handleRefresh(productId: number) {
    try {
      setError(null);
      const existingRow = rows.find((row) => row.id === productId);
      if (!existingRow) {
        throw new Error("Product not found.");
      }

      const result = await refreshProduct(productId);
      const price = Number(result.price.value);
      const previousPrice = existingRow.price;
      const priceChange = price - previousPrice;
      const priceChangePercent =
        previousPrice !== 0 ? (priceChange / previousPrice) * 100 : null;

      let trend: "up" | "down" | "stable" = "stable";
      if (price > previousPrice) {
        trend = "up";
      } else if (price < previousPrice) {
        trend = "down";
      }

      setRows((current) =>
        current.map((row) =>
          row.id !== productId
            ? row
            : {
                ...row,
                name: result.product.name,
                imageUrl: result.product.image_url,
                price,
                previousPrice,
                priceChange,
                priceChangePercent,
                currency: result.price.currency,
                availability: result.price.availability,
                sourceUrl: result.source.url,
                sourceDomain: result.source.domain,
                fetchedAt: result.price.fetched_at,
                trend,
              },
        ),
      );
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "Unable to refresh product",
      );
    }
  }

  // --------------------------------------------------
  // DELETE PRODUCT
  // --------------------------------------------------
  async function handleDelete(productId: number) {
    const confirmed = window.confirm(
      "Are you sure you want to delete this product?",
    );
    if (!confirmed) {
      return;
    }

    try {
      setError(null);
      await deleteProduct(productId);
      setRows((current) => current.filter((row) => row.id !== productId));
    } catch (err) {
      console.error(err);
      setError(
        err instanceof Error ? err.message : "Unable to delete product",
      );
    }
  }

  // --------------------------------------------------
  // SUMMARY METRICS
  // --------------------------------------------------
  const totalProducts = rows.length;

  const totalItems = rows.reduce(
    (total, row) => total + Number(row.quantity || 1),
    0,
  );

  const totalCurrentPrice = rows.reduce((total, row) => {
    const price = Number(row.price || 0);
    const quantity = Number(row.quantity || 1);
    return total + price * quantity;
  }, 0);

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------
  return (
    <main className="app">
      {/* -------------------------------------------- */}
      {/* HEADER */}
      {/* -------------------------------------------- */}
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
              PDF Catalog & Pricing
            </span>
          </h1>
          <p style={{ margin: 0, color: "#64748b" }}>
            Supplier Catalog Pricing, Direct PDF Ingestion & Quotation Costing
          </p>
        </div>
      </header>

      {/* -------------------------------------------- */}
      {/* SUMMARY NOTIFICATION BANNER */}
      {/* -------------------------------------------- */}
      {uploadNotification && (
        <section
          className={`catalog-notification-banner ${
            uploadNotification.type === "success"
              ? "catalog-notification-banner--success"
              : "catalog-notification-banner--info"
          }`}
          data-testid="catalog-notification-banner"
          style={{
            margin: "0 32px 16px",
            padding: "12px 18px",
            borderRadius: "8px",
            backgroundColor:
              uploadNotification.type === "success" ? "#dcfce7" : "#fef3c7",
            color: uploadNotification.type === "success" ? "#166534" : "#92400e",
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
                Supplier: {uploadNotification.summary.supplier_name || "Siemens"} |
                Total rows: {uploadNotification.summary.total_rows} |
                Imported: {uploadNotification.summary.imported_rows}
              </span>
            )}
          </div>
          <button
            type="button"
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
            data-testid="dismiss-notification-btn"
          >
            ✕
          </button>
        </section>
      )}

      {/* -------------------------------------------- */}
      {/* CATALOG PDF UPLOAD INTEGRATION */}
      {/* -------------------------------------------- */}
      <section
        className="catalog-upload-container"
        style={{ padding: "0 32px" }}
        data-testid="catalog-upload-wrapper"
      >
        <CatalogUpload
          defaultSupplier="Siemens"
          onUploadSuccess={handleCatalogUploadSuccess}
          onUploadError={(err) => setError(err.message)}
        />
      </section>

      {/* -------------------------------------------- */}
      {/* SUMMARY STATS */}
      {/* -------------------------------------------- */}
      <section className="summary">
        <div className="summary-card">
          <span>Total Products</span>
          <strong>{totalProducts}</strong>
        </div>

        <div className="summary-card">
          <span>Total Items</span>
          <strong>{totalItems}</strong>
        </div>

        <div className="summary-card">
          <span>Total Current Value</span>
          <strong>₹{totalCurrentPrice.toFixed(2)}</strong>
        </div>
      </section>

      {/* -------------------------------------------- */}
      {/* ERROR DISPLAY */}
      {/* -------------------------------------------- */}
      {error && (
        <div className="error" style={{ margin: "0 32px 16px" }}>
          {error}
        </div>
      )}

      {/* -------------------------------------------- */}
      {/* PRODUCT GRID */}
      {/* -------------------------------------------- */}
      <section className="grid-container">
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
            onRowsChange={setRows}
            onRefresh={handleRefresh}
            onDelete={handleDelete}
          />
        )}
      </section>
    </main>
  );
}

export default App;