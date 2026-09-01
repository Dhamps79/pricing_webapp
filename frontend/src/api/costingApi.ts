const API_BASE_URL = "http://127.0.0.1:8000";

export async function exportCostingSheet(sheetId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/costing-sheets/${sheetId}/export`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Failed to export Excel file");
  }

  // Create a Blob from the response
  const blob = await response.blob();
  
  // Create a download link and trigger it
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `Costing_Sheet_${sheetId}.xlsx`;
  document.body.appendChild(a);
  a.click();
  
  // Cleanup
  a.remove();
  window.URL.revokeObjectURL(url);
}