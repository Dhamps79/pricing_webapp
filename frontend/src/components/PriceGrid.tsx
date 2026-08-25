import { useMemo } from "react";
import type { ColDef } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import type { ProductRow } from "../types/price";


interface PriceGridProps {
  rows: ProductRow[];

onRowsChange: React.Dispatch<
    React.SetStateAction<ProductRow[]>
  >;

  onRefresh: (
    productId: number,
  ) => void;

  onDelete: (
    productId: number,
  ) => void;
}

export default function PriceGrid({
  rows,
  onRowsChange,
  onRefresh,
  onDelete
}: PriceGridProps) {
  const columnDefs = useMemo<ColDef<ProductRow>[]>(
  () => [
    {
      field: "name",
      headerName: "Product",
      flex: 2,
      sortable: true,
      filter: true,
    },

    {
      field: "price",
      headerName: "Price",
      sortable: true,
      filter: "agNumberColumnFilter",
      valueFormatter: (params) =>
        params.value != null
          ? `₹${Number(params.value).toLocaleString("en-IN")}`
          : "",
    },

    {
      field: "currency",
      headerName: "Currency",
      width: 100,
      sortable: true,
      filter: true,
    },

    {
      field: "availability",
      headerName: "Availability",
      flex: 1,
      sortable: true,
      filter: true,
    },

    {
      field: "fetchedAt",
      headerName: "Last Updated",
      flex: 1.5,
      sortable: true,
      filter: true,
    },

    {
      field: "trend",
      headerName: "Trend",
      width: 110,
      sortable: true,
      filter: true,
    },

    {
      field: "quantity",
      headerName: "Quantity",
      width: 110,
      editable: true,
      sortable: true,
      filter: "agNumberColumnFilter",
    },

    {
      field: "targetPrice",
      headerName: "Target Price",
      width: 130,
      editable: true,
      sortable: true,
      filter: "agNumberColumnFilter",
    },

    {
      field: "notes",
      headerName: "Notes",
      flex: 1.5,
      editable: true,
      sortable: true,
      filter: true,
    },
    {
  headerName: "Total",
  valueGetter: (params) => {
    const price = Number(params.data?.price || 0);
    const quantity = Number(
      params.data?.quantity || 1,
    );

    return price * quantity;
  },
},


    {
      headerName: "Actions",
      width: 180,
      sortable: false,
      filter: false,

      cellRenderer: (params: any) => {
        const productId = params.data?.id;

        return (
          <div
            style={{
              display: "flex",
              gap: "8px",
            }}
          >
            <button
              type="button"
              onClick={() => {
                if (productId) {
                  onRefresh(productId);
                }
              }}
            >
              Refresh
            </button>

            <button
              type="button"
              onClick={() => {
                if (productId) {
                  onDelete(productId);
                }
              }}
            >
              Delete
            </button>
          </div>
        );
      },
    },
  ],
  [onRefresh, onDelete],
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
      <AgGridReact<ProductRow>
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