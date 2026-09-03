import type { Product } from "../types/product";
import type { ProductRow } from "../types/price";


export function productToRow(
  product: Product,
): ProductRow {
  return {
    id: product.id,

    name: product.name,

    imageUrl: product.image_url,

    price:
      product.current_price ?? 0,

    previousPrice:
      product.previous_price,

    priceChange:
      product.price_change,

    priceChangePercent:
      product.price_change_percent,

    currency:
      product.currency ?? "INR",

    availability:
      product.availability,

    sourceUrl:
      product.source_url,

    sourceDomain:
      product.source_domain,

    fetchedAt:
      product.fetched_at,

    trend:
      product.trend,

    quantity: 1,

    targetPrice: null,

    notes: "",
  };
}