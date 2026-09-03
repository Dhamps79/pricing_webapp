
const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

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