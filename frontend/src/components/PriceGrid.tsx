import { useMemo } from "react";
import type { ColDef } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import type { CatalogRow } from "../types/catalog";

interface PriceGridProps {
  rows: CatalogRow[];
  onAddToSheet: (item: CatalogRow) => void;
  onDelete: (productId: number) => void;
  onSelectionChanged?: (selectedRows: CatalogRow[]) => void;
}

export default function PriceGrid({
  rows,
  onAddToSheet,
  onDelete,
  onSelectionChanged,
}: PriceGridProps) {

  const columnDefs = useMemo<ColDef<CatalogRow>[]>(
    () => [
      {
        headerCheckboxSelection: true,
        checkboxSelection: true,
        width: 50,
        pinned: "left",
        lockPosition: "left",
        suppressMenu: true,
        sortable: false,
        filter: false,
        resizable: false,
      },
      {
        field: "productCode",
        headerName: "Product Code",
        width: 170,
        sortable: true,
        filter: true,
        pinned: "left",
      },
      {
        field: "name",
        headerName: "Product Name",
        flex: 2,
        sortable: true,
        filter: true,
        minWidth: 200,
      },
      {
        field: "description",
        headerName: "Description",
        flex: 1.5,
        sortable: true,
        filter: true,
        minWidth: 150,
      },
      {
        field: "category",
        headerName: "Category",
        width: 140,
        sortable: true,
        filter: true,
      },
      {
        field: "unit",
        headerName: "Unit",
        width: 80,
        sortable: true,
        filter: true,
      },
      {
        field: "price",
        headerName: "Price (₹)",
        width: 130,
        sortable: true,
        filter: "agNumberColumnFilter",
        valueFormatter: (params) =>
          params.value != null
            ? `₹${Number(params.value).toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`
            : "—",
      },
      {
        field: "currency",
        headerName: "Currency",
        width: 90,
        sortable: true,
        filter: true,
      },
      {
        headerName: "Actions",
        width: 180,
        sortable: false,
        filter: false,
        pinned: "right",
        cellRenderer: (params: any) => {
          const row = params.data as CatalogRow | undefined;
          if (!row) return null;

          return (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <button
                type="button"
                style={{
                  padding: "4px 10px",
                  fontSize: "11px",
                  fontWeight: 600,
                  borderRadius: "4px",
                  border: "none",
                  background: "#2563eb",
                  color: "#fff",
                  cursor: "pointer",
                }}
                onClick={() => onAddToSheet(row)}
              >
                + Add to Sheet
              </button>

              <button
                type="button"
                style={{
                  padding: "4px 8px",
                  fontSize: "11px",
                  borderRadius: "4px",
                  border: "1px solid #e2e8f0",
                  background: "transparent",
                  color: "#94a3b8",
                  cursor: "pointer",
                }}
                onClick={() => onDelete(row.id)}
              >
                Delete
              </button>
            </div>
          );
        },
      },
    ],
    [onAddToSheet, onDelete],
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: true,
      sortable: true,
      filter: true,
    }),
    [],
  );

  return (
    <div
      className="ag-theme-quartz"
      style={{
        width: "100%",
        height: "600px",
      }}
    >
      <AgGridReact<CatalogRow>
        rowData={rows}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        pagination={false}
        animateRows={true}
        rowSelection="multiple"
        suppressRowClickSelection={true}
        onSelectionChanged={(params) => {
          if (onSelectionChanged) {
            const selected = params.api.getSelectedRows();
            onSelectionChanged(selected);
          }
        }}
      />
    </div>
  );
}