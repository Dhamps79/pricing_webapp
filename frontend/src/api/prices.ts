const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "/api/v1";

export async function trackPrice(url: string) {
  const response = await fetch(
    `${API_BASE_URL}/prices/track?url=${encodeURIComponent(url)}`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to track price: ${response.status}`);
  }

  return response.json();
}