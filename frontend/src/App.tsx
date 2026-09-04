import { useEffect, useState } from "react";

import PriceGrid from "./components/PriceGrid.tsx";

import type { ProductRow } from "./types/price";

import { trackPrice } from "./api/prices.ts";

import {
  getProducts,
  refreshProduct,
  deleteProduct,
} from "./services/productApi";

import { productToRow } from "./utils/productMapper";


function App() {
  const [rows, setRows] = useState<ProductRow[]>([]);

  const [url, setUrl] = useState("");

  const [loading, setLoading] = useState(true);

  const [tracking, setTracking] = useState(false);

  const [error, setError] = useState<string | null>(null);


  // --------------------------------------------------
  // LOAD PRODUCTS
  // --------------------------------------------------

  useEffect(() => {
    async function loadProducts() {
      try {
        setLoading(true);
        setError(null);

        const products = await getProducts();

        /*
         * Backend Product[]
         *        ↓
         * productToRow()
         *        ↓
         * Frontend ProductRow[]
         */
        setRows(
          products.map(productToRow),
        );
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
  // TRACK NEW PRODUCT
  // --------------------------------------------------

  async function handleTrack() {
    const trimmedUrl = url.trim();

    if (!trimmedUrl) {
      setError("Please enter a product URL.");
      return;
    }

    try {
      setTracking(true);
      setError(null);

      const result = await trackPrice(trimmedUrl);

      const row: ProductRow = {
        id: result.product.id,

        name: result.product.name,

        imageUrl: result.product.image_url,

        price: Number(result.price.value),

        previousPrice: null,

        priceChange: null,

        priceChangePercent: null,

        currency: result.price.currency,

        availability:
          result.price.availability,

        sourceUrl:
          result.source.url,

        sourceDomain:
          result.source.domain,

        fetchedAt:
          result.price.fetched_at,

        trend: "stable",

        // Spreadsheet fields
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
            item.id === row.id
              ? {
                  ...row,

                  // Preserve spreadsheet data
                  quantity: item.quantity,
                  targetPrice: item.targetPrice,
                  notes: item.notes,
                }
              : item,
          );
        }

        return [
          ...current,
          row,
        ];
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
  // REFRESH PRODUCT
  // --------------------------------------------------

  async function handleRefresh(
  productId: number,
) {
  try {
    setError(null);

    const existingRow = rows.find(
      (row) => row.id === productId,
    );

    if (!existingRow) {
      throw new Error("Product not found.");
    }

    const result =
      await refreshProduct(productId);

    const price =
      Number(result.price.value);

    const previousPrice =
      existingRow.price;

    const priceChange =
      price - previousPrice;

    const priceChangePercent =
      previousPrice !== 0
        ? (priceChange / previousPrice) * 100
        : null;

    let trend:
      | "up"
      | "down"
      | "stable" = "stable";

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
              imageUrl:
                result.product.image_url,

              price,
              previousPrice,
              priceChange,
              priceChangePercent,

              currency:
                result.price.currency,

              availability:
                result.price.availability,

              sourceUrl:
                result.source.url,

              sourceDomain:
                result.source.domain,

              fetchedAt:
                result.price.fetched_at,

              trend,
            },
      ),
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

  async function handleDelete(
    productId: number,
  ) {
    const confirmed =
      window.confirm(
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
          (row) => row.id !== productId,
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
  // SUMMARY
  // --------------------------------------------------

  const totalProducts =
    rows.length;


  const totalItems =
    rows.reduce(
      (total, row) =>
        total +
        Number(
          row.quantity || 1,
        ),
      0,
    );


  const totalCurrentPrice =
    rows.reduce(
      (total, row) => {
        const price =
          Number(
            row.price || 0,
          );

        const quantity =
          Number(
            row.quantity || 1,
          );

        return (
          total +
          price * quantity
        );
      },
      0,
    );


  // --------------------------------------------------
  // LOADING
  // --------------------------------------------------

  if (loading) {
    return (
      <main className="app">

        <h1>
          Live Spreadsheet
        </h1>

        <p>
          Loading products...
        </p>

      </main>
    );
  }


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

          <h1>
            Live Spreadsheet
          </h1>

          <p>
            Track product prices
            from online sources.
          </p>

        </div>

      </header>


      {/* -------------------------------------------- */}
      {/* SUMMARY */}
      {/* -------------------------------------------- */}

      <section className="summary">

        <div className="summary-card">

          <span>
            Total Products
          </span>

          <strong>
            {totalProducts}
          </strong>

        </div>


        <div className="summary-card">

          <span>
            Total Items
          </span>

          <strong>
            {totalItems}
          </strong>

        </div>


        <div className="summary-card">

          <span>
            Total Current Value
          </span>

          <strong>
            ₹
            {totalCurrentPrice.toFixed(2)}
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
          disabled={tracking}
        />


        <button
          type="button"
          onClick={handleTrack}
          disabled={
            tracking ||
            !url.trim()
          }
        >
          {tracking
            ? "Tracking..."
            : "Track Price"}
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
      {/* PRODUCT GRID */}
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