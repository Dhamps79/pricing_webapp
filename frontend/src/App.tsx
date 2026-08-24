import { useEffect, useState } from "react";
import PriceGrid from "./components/PriceGrid.tsx";
import type { ProductRow } from "./types/price";
import { trackPrice } from "./api/prices.ts";

import {
  getProducts,
  refreshProduct,
  type Product,
} from "./services/productApi";

function App() {
  const [rows, setRows] = useState<ProductRow[]>([]);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /*
   * Load existing products from PostgreSQL
   * when the application starts.
   */
  useEffect(() => {
    async function loadProducts() {
      try {
        setLoading(true);
        setError(null);

        const products = await getProducts();

        /*
         * Convert backend Product objects into
         * the row structure expected by AG Grid.
         */
        const productRows: ProductRow[] = products.map(
          (product: Product) => ({
            id: product.id,
            name: product.name,
            imageUrl: product.image_url,

            price: Number(product.current_price ?? 0),
            currency: product.currency ?? "INR",

            availability:
              product.availability ?? "Unknown",

            sourceUrl: product.source_url ?? "",
            sourceDomain:
              product.source_domain ?? "",

            fetchedAt: product.fetched_at ?? "",

            trend: product.trend,

            quantity: 1,
            targetPrice: null,
            notes: "",
          }),
        );

        setRows(productRows);
      } catch (err) {
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

  /*
   * Track a new product from a URL.
   */
  async function handleTrack() {
    if (!url.trim()) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
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
      setError(
        err instanceof Error
          ? err.message
          : "Unable to track product",
      );
    } finally {
      setLoading(false);
    }
  }

  /*
   * Refresh the price of one product.
   */
  async function refreshProduct(productId: number) {
    const row = rows.find(
      (item) => item.id === productId,
    );

    if (!row) {
      return;
    }

    try {
      setError(null);

      const response = await fetch(
        `http://127.0.0.1:8000/api/v1/prices/track?url=${encodeURIComponent(
          row.sourceUrl,
        )}`,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new Error("Price refresh failed");
      }

      const result = await response.json();

      setRows((current) =>
        current.map((item) => {
          if (item.id !== productId) {
            return item;
          }

          const oldPrice = item.price;

          const newPrice = Number(
            result.price.value,
          );

          let trend: ProductRow["trend"] =
            "stable";

          if (newPrice > oldPrice) {
            trend = "up";
          } else if (newPrice < oldPrice) {
            trend = "down";
          }

          return {
            ...item,

            price: newPrice,

            currency:
              result.price.currency,

            availability:
              result.price.availability,

            fetchedAt:
              result.price.fetched_at,

            trend,
          };
        }),
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Price refresh failed",
      );
    }
  }

  /*
   * Show loading state while PostgreSQL data
   * is initially being loaded.
   */
  if (loading && rows.length === 0) {
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
            Track product prices from online
            sources.
          </p>
        </div>
      </header>

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
          onClick={handleTrack}
          disabled={loading || !url.trim()}
        >
          {loading
            ? "Tracking..."
            : "Track Price"}
        </button>
      </section>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <section className="grid-container">
        <PriceGrid
          rows={rows}
          onRowsChange={setRows}
          onRefresh={handleRefresh}
        />
      </section>
    </main>
  );
}

export default App;