import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";

import type { ColDef } from "ag-grid-community";

import type { Product } from "../services/productApi";


interface PriceGridProps {
  rows: ProductRow[];

  onRowsChange: (
    rows: ProductRow[],
  ) => void;

  onRefresh: (
    productId: number,
  ) => void;
}

export default function PriceGrid({
  rows,
  onRowsChange,
  onRefresh,
}: PriceGridProps) {
  const columnDefs = useMemo<ColDef<Product>[]>(
    () => [
      {
        field: "name",
        headerName: "Product",
        sortable: true,
        filter: true,
        flex: 2,
      },

      {
        field: "current_price",
        headerName: "Current Price",
        sortable: true,
        filter: "agNumberColumnFilter",
        valueFormatter: (params) => {
          if (params.value == null) {
            return "—";
          }

          return `${params.value}`;
        },
      },

      {
        field: "previous_price",
        headerName: "Previous Price",
        sortable: true,
        filter: "agNumberColumnFilter",
      },

      {
        field: "price_change",
        headerName: "Change",
        sortable: true,
        filter: "agNumberColumnFilter",
      },

      {
        field: "price_change_percent",
        headerName: "Change %",
        sortable: true,
        filter: "agNumberColumnFilter",

        valueFormatter: (params) => {
          if (params.value == null) {
            return "—";
          }

          return `${Number(params.value).toFixed(2)}%`;
        },
      },

      {
        field: "currency",
        headerName: "Currency",
        width: 100,
      },

      {
        field: "availability",
        headerName: "Availability",
        sortable: true,
        filter: true,
      },

      {
        field: "source_domain",
        headerName: "Source",
        sortable: true,
        filter: true,
      },

      {
        field: "fetched_at",
        headerName: "Last Updated",
        sortable: true,
        flex: 1,
      },

      {
        field: "trend",
        headerName: "Trend",
        sortable: true,
        filter: true,
      },

      {
  headerName: "Actions",
  width: 120,
  sortable: false,
  filter: false,

  cellRenderer: (params: any) => {
    const productId = params.data?.id;

    return (
      <button
        onClick={() =>
          onRefresh(productId)
        }
      >
        Refresh
      </button>
    );
  },
  },
    ],
    []
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: true,
      sortable: true,
      filter: true,
    }),
    []
  );

  return (
    <div
      className="ag-theme-quartz"
      style={{
        width: "100%",
        height: "600px",
      }}
    >
      <AgGridReact<Product>
        rowData={rows}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        pagination={true}
        paginationPageSize={20}
        onCellValueChanged={(event) => {
          if (!event.data) {
            return;
          }

          onRowsChange(
            rows.map((row) =>
              row.id === event.data!.id
                ? event.data!
                : row
            )
          );
        }}
      />
    </div>
  );
}