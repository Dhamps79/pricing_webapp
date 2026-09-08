import { useState, useRef, useEffect, type DragEvent, type ChangeEvent } from "react";
import type { CatalogUploadResponse } from "../types/catalog";
import { uploadCatalogPdf } from "../services/catalogApi";
import "./CatalogUpload.css";

export interface CatalogUploadProps {
  /**
   * Callback fired immediately when a catalog upload completes successfully.
   * Passes the backend response to trigger grid auto-refresh.
   */
  onUploadSuccess?: (response: CatalogUploadResponse) => void;

  /**
   * Optional callback fired when an upload fails.
   */
  onUploadError?: (error: Error) => void;

  /**
   * Default supplier name (default: "Siemens").
   */
  defaultSupplier?: string;

  /**
   * Optional additional class name.
   */
  className?: string;
}

export type UploadState =
  | "idle"        // Ready for file selection
  | "selected"    // File picked, ready to upload
  | "uploading"   // Sending bytes over network (0-100%)
  | "parsing"     // Backend coordinate extraction & entity creation
  | "completed"   // Finished successfully
  | "failed";     // Error occurred

export function CatalogUpload({
  onUploadSuccess,
  onUploadError,
  defaultSupplier = "Siemens",
  className = "",
}: CatalogUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [supplierName, setSupplierName] = useState<string>(defaultSupplier);
  const [status, setStatus] = useState<UploadState>("idle");
  const [progress, setProgress] = useState<number>(0);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [result, setResult] = useState<CatalogUploadResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);

  // Active ticking elapsed timer during uploading and parsing states
  useEffect(() => {
    if (status === "uploading" || status === "parsing") {
      startTimeRef.current = Date.now();
      timerRef.current = window.setInterval(() => {
        setElapsedSeconds(Number(((Date.now() - startTimeRef.current) / 1000).toFixed(1)));
      }, 100);
    } else {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [status]);

  // Client-side file validation
  const validateAndSetFile = (selectedFile: File) => {
    setErrorMessage(null);

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setErrorMessage("Only PDF files are supported (.pdf).");
      return;
    }

    if (selectedFile.size === 0) {
      setErrorMessage("The selected PDF file is empty (0 bytes).");
      return;
    }

    const MAX_SIZE = 50 * 1024 * 1024; // 50 MB
    if (selectedFile.size > MAX_SIZE) {
      setErrorMessage("File exceeds the maximum allowed size of 50 MB.");
      return;
    }

    setFile(selectedFile);
    setStatus("selected");
    setProgress(0);
    setResult(null);
  };

  // Drag and drop handlers
  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  // Trigger catalog upload
  const handleStartUpload = async () => {
    if (!file) return;

    setStatus("uploading");
    setProgress(0);
    setErrorMessage(null);

    try {
      const response = await uploadCatalogPdf(file, {
        supplierName: supplierName.trim() || undefined,
        onProgress: ({ percent }) => {
          setProgress(percent);
          if (percent >= 100) {
            setStatus("parsing");
          }
        },
      });

      // Calculate final duration if startTime was recorded
      if (startTimeRef.current > 0) {
        setElapsedSeconds(Number(((Date.now() - startTimeRef.current) / 1000).toFixed(1)));
      }

      setStatus("completed");
      setResult(response);

      if (onUploadSuccess) {
        onUploadSuccess(response);
      }
    } catch (err: any) {
      const msg = err instanceof Error ? err.message : "Upload failed unexpectedly.";
      setErrorMessage(msg);
      setStatus("failed");

      if (onUploadError) {
        onUploadError(err instanceof Error ? err : new Error(msg));
      }
    }
  };

  // Reset to initial state
  const handleReset = () => {
    setFile(null);
    setStatus("idle");
    setProgress(0);
    setResult(null);
    setErrorMessage(null);
    setElapsedSeconds(0);
    startTimeRef.current = 0;
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className={`catalog-upload-card ${className}`}>
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".pdf,application/pdf"
        style={{ display: "none" }}
        onChange={handleFileInputChange}
        data-testid="catalog-file-input"
      />

      {/* State: IDLE or SELECTED */}
      {(status === "idle" || status === "selected") && !result && (
        <div className="catalog-upload-input-section">
          <div
            className={`catalog-dropzone ${isDragging ? "catalog-dropzone--active" : ""}`}
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            data-testid="catalog-dropzone"
          >
            <div className="catalog-dropzone-icon">
              <svg
                width="36"
                height="36"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="12" y1="18" x2="12" y2="12" />
                <line x1="9" y1="15" x2="12" y2="12" />
                <line x1="15" y1="15" x2="12" y2="12" />
              </svg>
            </div>

            <div className="catalog-dropzone-text">
              <span className="catalog-dropzone-primary">
                <strong>Click to browse</strong> or drag & drop supplier catalog PDF
              </span>
              <span className="catalog-dropzone-secondary">
                Accepts manufacturer price lists (.pdf) up to 50MB (e.g., Siemens Betagard)
              </span>
            </div>
          </div>

          {/* Selected File Details Bar */}
          {file && status === "selected" && (
            <div className="catalog-selected-bar" data-testid="catalog-selected-bar">
              <div className="catalog-file-info">
                <span className="catalog-file-badge">PDF</span>
                <span className="catalog-file-name" title={file.name}>
                  {file.name}
                </span>
                <span className="catalog-file-size">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </span>
              </div>

              <div className="catalog-supplier-select">
                <label htmlFor="supplier-name-input">Supplier:</label>
                <input
                  id="supplier-name-input"
                  type="text"
                  value={supplierName}
                  onChange={(e) => setSupplierName(e.target.value)}
                  placeholder="e.g. Siemens"
                  className="catalog-supplier-input"
                  data-testid="supplier-name-input"
                />
              </div>

              <div className="catalog-action-group">
                <button
                  type="button"
                  onClick={handleStartUpload}
                  className="catalog-btn catalog-btn--primary"
                  data-testid="catalog-upload-btn"
                >
                  Upload & Import Catalog
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="catalog-btn catalog-btn--secondary"
                  title="Clear file"
                  data-testid="catalog-cancel-btn"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* State: UPLOADING or PARSING */}
      {(status === "uploading" || status === "parsing") && (
        <div className="catalog-progress-section" data-testid="catalog-progress-section">
          <div className="catalog-status-header">
            <div className="catalog-status-badge-container">
              {status === "uploading" ? (
                <span className="catalog-badge catalog-badge--uploading" data-testid="status-uploading">
                  <span className="catalog-spinner" /> Uploading PDF ({progress}%)...
                </span>
              ) : (
                <span className="catalog-badge catalog-badge--parsing" data-testid="status-parsing">
                  <span className="catalog-spinner catalog-spinner--amber" /> Parsing {supplierName || "Siemens"} PDF & Extracting Prices...
                </span>
              )}
            </div>

            <div className="catalog-timer" data-testid="catalog-timer">
              ⏱ Elapsed: <strong>{elapsedSeconds.toFixed(1)}s</strong>
            </div>
          </div>

          {/* Real-time Progress Bar */}
          <div className="catalog-progressbar-track">
            <div
              className={`catalog-progressbar-fill ${status === "parsing" ? "catalog-progressbar-fill--pulse" : ""}`}
              style={{ width: `${Math.max(5, progress)}%` }}
              data-testid="catalog-progressbar-fill"
            />
          </div>

          <div className="catalog-progress-footer">
            <span className="catalog-progress-filename">{file?.name}</span>
            <span className="catalog-progress-phase">
              {status === "uploading"
                ? `${progress}% transmitted`
                : "Analyzing coordinate clusters & saving items..."}
            </span>
          </div>
        </div>
      )}

      {/* State: COMPLETED (4-Metric Summary Feedback Presentation) */}
      {status === "completed" && result && (
        <div className="catalog-summary-section" data-testid="catalog-summary-section">
          <div className="catalog-summary-header">
            <div className="catalog-summary-title">
              <span className="catalog-badge catalog-badge--completed" data-testid="status-completed">
                ✓ Catalog Import Completed
              </span>
              <span className="catalog-summary-meta">
                {result.file_name} • Supplier: {result.supplier_name || "Siemens"}
              </span>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="catalog-btn catalog-btn--outline"
              data-testid="catalog-upload-another-btn"
            >
              Upload Another Catalog
            </button>
          </div>

          {/* 4-Tile Feedback Metric Grid */}
          <div className="catalog-metrics-grid">
            <div
              className="catalog-metric-card catalog-metric-card--success"
              data-testid="catalog-metric-imported-rows"
            >
              <span className="catalog-metric-label">Imported Rows</span>
              <strong className="catalog-metric-value">{result.imported_rows}</strong>
              <span className="catalog-metric-sub">Added to catalog</span>
            </div>

            <div className="catalog-metric-card" data-testid="catalog-metric-total-rows">
              <span className="catalog-metric-label">Total Extracted</span>
              <strong className="catalog-metric-value">{result.total_rows}</strong>
              <span className="catalog-metric-sub">PDF line items</span>
            </div>

            <div
              className={`catalog-metric-card ${result.failed_rows > 0 ? "catalog-metric-card--warning" : ""}`}
              data-testid="catalog-metric-failed-rows"
            >
              <span className="catalog-metric-label">Failed Rows</span>
              <strong className="catalog-metric-value">{result.failed_rows}</strong>
              <span className="catalog-metric-sub">Parse errors</span>
            </div>

            <div className="catalog-metric-card" data-testid="catalog-metric-elapsed-time">
              <span className="catalog-metric-label">Elapsed Time</span>
              <strong className="catalog-metric-value">{elapsedSeconds.toFixed(1)}s</strong>
              <span className="catalog-metric-sub">Processing duration</span>
            </div>
          </div>

          <div className="catalog-autorefresh-indicator">
            <span className="catalog-pulse-dot" /> Catalog products spreadsheet automatically refreshed below.
          </div>
        </div>
      )}

      {/* State: FAILED / ERROR ALERT */}
      {errorMessage && (
        <div className="catalog-alert catalog-alert--error" data-testid="catalog-error-alert">
          <div className="catalog-alert-icon">⚠️</div>
          <div className="catalog-alert-content">
            <strong>Upload Error:</strong> {errorMessage}
          </div>
          <button
            type="button"
            className="catalog-alert-close"
            onClick={() => setErrorMessage(null)}
            title="Dismiss"
            data-testid="catalog-dismiss-error-btn"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
};

export default CatalogUpload;
