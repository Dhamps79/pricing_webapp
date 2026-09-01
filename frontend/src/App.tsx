import { useEffect, useState } from "react";
import PriceGrid from "./components/PriceGrid.tsx";
import type { ProductRow } from "./types/price";
import { trackPrice } from "./api/prices.ts";
import {
  getProducts,
  deleteProduct,
} from "./services/productApi";
import { exportCostingSheet } from "./api/costingApi";
function App() {
  const [rows, setRows] = useState<ProductRow[]>([]);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [tracking, setTracking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --------------------------------------------------
  // LOAD PRODUCTS FROM POSTGRESQL
  // --------------------------------------------------

  useEffect(() => {
    async function loadProducts() {
      try {
        setLoading(true);
        setError(null);

        const products = await getProducts();

        setRows(products);
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
  }, []);

  // --------------------------------------------------
  // ADD / TRACK PRODUCT
  // --------------------------------------------------

  async function handleTrack() {
    if (!url.trim()) {
      return;
    }

    try {
      setTracking(true);
      setError(null);

      const result = await trackPrice(url);

      const row: ProductRow = {
        id: result.product.id,
        name: result.product.name,
        imageUrl: result.product.image_url,
        price: Number(result.price.value),
        currency: result.price.currency,
        availability: result.price.availability,
        sourceUrl: result.source.url,
        sourceDomain: result.source.domain,
        fetchedAt: result.price.fetched_at,
        trend: "stable",
        quantity: 1,
        targetPrice: null,
        notes: "",
      };

      setRows((current) => {
        const existing = current.find(
          (item) => item.id === row.id,
        );

        if (existing) {
          return current.map((item) =>
            item.id === row.id ? row : item,
          );
        }

        return [...current, row];
      });

      setUrl("");
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to track product",
      );
    } finally {
      setTracking(false);
    }
  }

  // --------------------------------------------------
  // REFRESH PRODUCT PRICE
  // --------------------------------------------------

  async function handleRefresh(productId: number) {
    try {
      setError(null);

      const row = rows.find(
        (item) => item.id === productId,
      );

      if (!row) {
        return;
      }

      const response = await fetch(
        `http://127.0.0.1:8000/api/v1/prices/${productId}/refresh`,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new Error(
          `Refresh failed (${response.status})`,
        );
      }

      const result = await response.json();

      setRows((current) =>
        current.map((item) => {
          if (item.id !== productId) {
            return item;
          }

          const oldPrice = Number(item.price);
          const newPrice = Number(result.price.value);

          let trend: ProductRow["trend"] = "stable";

          if (newPrice > oldPrice) {
            trend = "up";
          } else if (newPrice < oldPrice) {
            trend = "down";
          }

          return {
            ...item,
            price: newPrice,
            currency: result.price.currency,
            availability: result.price.availability,
            fetchedAt: result.price.fetched_at,
            trend,
          };
        }),
      );
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to refresh product",
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

      setRows((current) =>
        current.filter(
          (item) => item.id !== productId,
        ),
      );
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to delete product",
      );
    }
  }

  // --------------------------------------------------
  // CALCULATED SUMMARY
  // --------------------------------------------------

 const totalProducts = rows.length;

const totalItems = rows.reduce(
  (total, row) =>
    total + Number(row.quantity || 1),
  0,
);

const totalCurrentPrice = rows.reduce(
  (total, row) => {
    const price = Number(row.price || 0);
    const quantity = Number(row.quantity || 1);

    return total + price * quantity;
  },
  0,
);

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------

  if (loading) {
    return (
      <main className="app">
        <h1>Live Spreadsheet</h1>
        <p>Loading products...</p>
      </main>
    );
  }

  return (
    <main className="app">

      <header className="app-header">
        <div>
          <h1>Live Spreadsheet</h1>

          <p>
            Track product prices from online sources.
          </p>
        </div>
      </header>

      {/* -------------------------------------------- */}
      {/* SUMMARY */}
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
    <strong>
      ₹{totalCurrentPrice.toFixed(2)}
    </strong>
  </div>

</section>

      {/* -------------------------------------------- */}
      {/* ADD PRODUCT */}
      {/* -------------------------------------------- */}

      <section className="toolbar">

        <input
          type="url"
          value={url}
          onChange={(event) =>
            setUrl(event.target.value)
          }
          placeholder="Paste a product URL..."
        />

        <button
          type="button"
          onClick={handleTrack}
          disabled={tracking}
        >
          {tracking
            ? "Tracking..."
            : "Track Price"}
        </button>
        <button 
          type="button" 
          onClick={() => exportCostingSheet(currentSheetId)}
          className="export-button">
            Export to Excel
        </button>
      </section>

      {/* -------------------------------------------- */}
      {/* ERROR */}
      {/* -------------------------------------------- */}

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {/* -------------------------------------------- */}
      {/* GRID */}
      {/* -------------------------------------------- */}

      <section className="grid-container">

        <PriceGrid
          rows={rows}
          onRowsChange={setRows}
          onRefresh={handleRefresh}
          onDelete={handleDelete}
        />

      </section>

    </main>
  );
}

export default App;