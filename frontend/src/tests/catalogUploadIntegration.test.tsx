// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CatalogUpload } from "../components/CatalogUpload";
import App from "../App";
import * as catalogApi from "../services/catalogApi";
import * as productApi from "../services/productApi";

describe("CatalogUpload Component & App Integration Tests", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("CatalogUpload Component Interactions", () => {
    it("renders idle state with drag-and-drop zone and hidden file input", () => {
      render(<CatalogUpload />);

      expect(screen.getByTestId("catalog-dropzone")).toBeInTheDocument();
      expect(screen.getByTestId("catalog-file-input")).toBeInTheDocument();
      expect(
        screen.getByText(/Click to browse or drag & drop supplier catalog PDF/i),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId("catalog-selected-bar"),
      ).not.toBeInTheDocument();
    });

    it("rejects non-PDF files and shows inline alert", async () => {
      render(<CatalogUpload />);

      const fileInput = screen.getByTestId("catalog-file-input");
      const badFile = new File(["not a pdf"], "notes.txt", { type: "text/plain" });

      fireEvent.change(fileInput, { target: { files: [badFile] } });

      await waitFor(() => {
        expect(screen.getByTestId("catalog-error-alert")).toBeInTheDocument();
        expect(
          screen.getByText(/Only PDF files are supported \(\.pdf\)/i),
        ).toBeInTheDocument();
      });
    });

    it("rejects empty 0-byte PDF files and shows inline alert", async () => {
      render(<CatalogUpload />);

      const fileInput = screen.getByTestId("catalog-file-input");
      const emptyPdf = new File([], "empty.pdf", { type: "application/pdf" });

      fireEvent.change(fileInput, { target: { files: [emptyPdf] } });

      await waitFor(() => {
        expect(screen.getByTestId("catalog-error-alert")).toBeInTheDocument();
        expect(
          screen.getByText(/The selected PDF file is empty \(0 bytes\)/i),
        ).toBeInTheDocument();
      });
    });

    it("handles drag events and selects file upon drop", async () => {
      render(<CatalogUpload />);

      const dropzone = screen.getByTestId("catalog-dropzone");

      // Drag enter
      fireEvent.dragEnter(dropzone, {
        dataTransfer: { types: ["Files"] },
      });
      expect(dropzone.className).toContain("catalog-dropzone--active");

      // Drag leave
      fireEvent.dragLeave(dropzone);
      expect(dropzone.className).not.toContain("catalog-dropzone--active");

      // Drop
      const validPdf = new File(["%PDF-1.4 mock content"], "siemens-mcb.pdf", {
        type: "application/pdf",
      });
      fireEvent.drop(dropzone, {
        dataTransfer: { files: [validPdf] },
      });

      await waitFor(() => {
        expect(screen.getByTestId("catalog-selected-bar")).toBeInTheDocument();
        expect(screen.getByText("siemens-mcb.pdf")).toBeInTheDocument();
        expect(screen.getByTestId("catalog-upload-btn")).toBeInTheDocument();
      });
    });

    it("allows editing supplier name and clearing selected file", async () => {
      render(<CatalogUpload defaultSupplier="Siemens" />);

      const fileInput = screen.getByTestId("catalog-file-input");
      const validPdf = new File(["%PDF-1.4 content"], "catalog.pdf", {
        type: "application/pdf",
      });

      fireEvent.change(fileInput, { target: { files: [validPdf] } });

      expect(screen.getByTestId("catalog-selected-bar")).toBeInTheDocument();

      const supplierInput = screen.getByTestId("supplier-name-input") as HTMLInputElement;
      expect(supplierInput.value).toBe("Siemens");

      fireEvent.change(supplierInput, { target: { value: "Schneider Electric" } });
      expect(supplierInput.value).toBe("Schneider Electric");

      // Click clear button
      const cancelBtn = screen.getByTestId("catalog-cancel-btn");
      fireEvent.click(cancelBtn);

      expect(screen.queryByTestId("catalog-selected-bar")).not.toBeInTheDocument();
      expect(screen.getByTestId("catalog-dropzone")).toBeInTheDocument();
    });

    it("progresses through uploading, parsing, and completed states with 4-metric card", async () => {
      const mockSuccessResponse = {
        id: 1,
        file_name: "Siemens-Betagard.pdf",
        supplier_name: "Siemens",
        status: "completed",
        total_rows: 52,
        imported_rows: 52,
        failed_rows: 0,
        created_at: "2026-09-08T07:00:00Z",
        completed_at: "2026-09-08T07:00:04Z",
      };

      let progressCallback: ((info: { loaded: number; total: number; percent: number }) => void) | undefined;

      const uploadSpy = vi
        .spyOn(catalogApi, "uploadCatalogPdf")
        .mockImplementation((_file, options) => {
          if (typeof options === "object") {
            progressCallback = options.onProgress;
          }
          return new Promise((resolve) => {
            // Simulate progress ticks
            setTimeout(() => {
              progressCallback?.({ loaded: 50, total: 100, percent: 50 });
            }, 10);
            setTimeout(() => {
              progressCallback?.({ loaded: 100, total: 100, percent: 100 });
            }, 20);
            setTimeout(() => {
              resolve(mockSuccessResponse);
            }, 30);
          });
        });

      const onUploadSuccess = vi.fn();
      render(<CatalogUpload onUploadSuccess={onUploadSuccess} />);

      const fileInput = screen.getByTestId("catalog-file-input");
      const validPdf = new File(["%PDF-1.4 test"], "Siemens-Betagard.pdf", {
        type: "application/pdf",
      });

      fireEvent.change(fileInput, { target: { files: [validPdf] } });

      const uploadBtn = screen.getByTestId("catalog-upload-btn");
      fireEvent.click(uploadBtn);

      // Verify progress section appears
      await waitFor(() => {
        expect(screen.getByTestId("catalog-progress-section")).toBeInTheDocument();
        expect(screen.getByTestId("catalog-timer")).toBeInTheDocument();
      });

      // Verify completion state and 4 metrics
      await waitFor(() => {
        expect(screen.getByTestId("catalog-summary-section")).toBeInTheDocument();
        expect(screen.getByTestId("status-completed")).toBeInTheDocument();
      });

      expect(screen.getByTestId("catalog-metric-imported-rows")).toHaveTextContent("52");
      expect(screen.getByTestId("catalog-metric-total-rows")).toHaveTextContent("52");
      expect(screen.getByTestId("catalog-metric-failed-rows")).toHaveTextContent("0");
      expect(screen.getByTestId("catalog-metric-elapsed-time")).toBeInTheDocument();

      expect(uploadSpy).toHaveBeenCalled();
      expect(onUploadSuccess).toHaveBeenCalledWith(mockSuccessResponse);

      // Reset by clicking "Upload Another Catalog"
      const uploadAnotherBtn = screen.getByTestId("catalog-upload-another-btn");
      fireEvent.click(uploadAnotherBtn);

      expect(screen.queryByTestId("catalog-summary-section")).not.toBeInTheDocument();
      expect(screen.getByTestId("catalog-dropzone")).toBeInTheDocument();
    });

    it("displays error alert and calls onUploadError when upload fails", async () => {
      vi.spyOn(catalogApi, "uploadCatalogPdf").mockRejectedValue(
        new Error("Catalog PDF import failed: Syntax error on page 3"),
      );

      const onUploadError = vi.fn();
      render(<CatalogUpload onUploadError={onUploadError} />);

      const fileInput = screen.getByTestId("catalog-file-input");
      const validPdf = new File(["%PDF-1.4 test"], "bad-format.pdf", {
        type: "application/pdf",
      });

      fireEvent.change(fileInput, { target: { files: [validPdf] } });
      fireEvent.click(screen.getByTestId("catalog-upload-btn"));

      await waitFor(() => {
        expect(screen.getByTestId("catalog-error-alert")).toBeInTheDocument();
        expect(
          screen.getByText(/Syntax error on page 3/i),
        ).toBeInTheDocument();
      });

      expect(onUploadError).toHaveBeenCalled();

      // Dismiss error
      fireEvent.click(screen.getByTestId("catalog-dismiss-error-btn"));
      expect(screen.queryByTestId("catalog-error-alert")).not.toBeInTheDocument();
    });
  });

  describe("App.tsx Integration & Auto-Refresh Signaling", () => {
    it("renders CatalogUpload in toolbar and triggers auto-refresh upon successful upload", async () => {
      let getProductsCallCount = 0;
      vi.spyOn(productApi, "getProducts").mockImplementation(() => {
        getProductsCallCount++;
        return Promise.resolve([
          {
            id: 1,
            name: "Initial Product",
            brand_id: null,
            category_id: null,
            description: null,
            unit: null,
            image_url: null,
            is_active: true,
            current_price: null,
            previous_price: null,
            price_change: null,
            price_change_percent: null,
            currency: null,
            availability: null,
            source_url: null,
            source_domain: null,
            fetched_at: null,
            trend: "stable" as const,
            created_at: "2026-09-08T07:00:00Z",
            updated_at: "2026-09-08T07:00:00Z",
            prices: [],
            sources: [],
          },
        ]);
      });

      const mockUploadResponse = {
        id: 10,
        file_name: "Electrical-Installation-Products.pdf",
        supplier_name: "Siemens",
        status: "completed",
        total_rows: 52,
        imported_rows: 52,
        failed_rows: 0,
        created_at: "2026-09-08T07:00:00Z",
        completed_at: "2026-09-08T07:00:05Z",
      };

      vi.spyOn(catalogApi, "uploadCatalogPdf").mockResolvedValue(mockUploadResponse);

      render(<App />);

      // Initial load
      await waitFor(() => {
        expect(getProductsCallCount).toBe(1);
      });

      // Verify CatalogUpload is rendered in App toolbar
      expect(screen.getByTestId("catalog-upload-wrapper")).toBeInTheDocument();
      expect(screen.getByTestId("catalog-dropzone")).toBeInTheDocument();

      // Simulate file drop & upload
      const fileInput = screen.getByTestId("catalog-file-input");
      const validPdf = new File(["%PDF-1.4 bytes"], "Electrical-Installation-Products.pdf", {
        type: "application/pdf",
      });

      fireEvent.change(fileInput, { target: { files: [validPdf] } });

      await waitFor(() => {
        expect(screen.getByTestId("catalog-upload-btn")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("catalog-upload-btn"));

      // Wait for completion and notification banner
      await waitFor(() => {
        expect(screen.getByTestId("catalog-notification-banner")).toBeInTheDocument();
      });

      expect(screen.getByText(/Successfully imported 52 products/i)).toBeInTheDocument();
      expect(screen.getByText(/Supplier: Siemens/i)).toBeInTheDocument();

      // Verify declarative auto-refresh counter triggered getProducts again!
      expect(getProductsCallCount).toBe(2);

      // Verify dismissing notification banner works
      fireEvent.click(screen.getByTestId("dismiss-notification-btn"));
      expect(screen.queryByTestId("catalog-notification-banner")).not.toBeInTheDocument();
    });
  });
});
