# Handoff Report: Milestone 2 — Catalog PDF Upload Frontend Component Design & App Integration

## Executive Summary
This investigation delivers the complete architectural design and concrete implementation blueprint for the dedicated `CatalogUpload` component and its seamless integration into `frontend/src/App.tsx` for Milestone 2 (Catalog PDF Upload Integration). It addresses all requirements from `ORIGINAL_REQUEST.md` (§R1, §R4) and `PROJECT.md` (Features F1, F2, F3): drag-and-drop zone, file input selector (.pdf), upload trigger button, real-time progress bar with live spinner and status badges (`Uploading...`, `Parsing Siemens PDF...`, `Completed`, `Failed`), 4-metric summary feedback card (imported rows, failed rows, total extracted, elapsed time), toast alerts, and uncluttered integration into the application header/toolbar with auto-refresh signaling.

---

## 1. Observation

### 1.1 Existing Application Structure in `frontend/src/App.tsx`
Inspection of `frontend/src/App.tsx` (lines 1–508) reveals the current layout and state architecture:
- **Header Structure** (`App.tsx` lines 376–392):
  ```tsx
  <header className="app-header">
    <div>
      <h1>Live Spreadsheet</h1>
      <p>Track product prices from online sources.</p>
    </div>
  </header>
  ```
  The header is currently a single-column block with a static title and subtitle. It has plenty of horizontal real estate (currently empty on the right side) to host upload controls or an upload action trigger.
- **Summary Section** (`App.tsx` lines 398–440):
  Contains three metric cards: "Total Products" (`totalProducts`), "Total Items" (`totalItems`), and "Total Current Value" (`totalCurrentPrice`).
- **Toolbar Section** (`App.tsx` lines 446–473):
  ```tsx
  <section className="toolbar">
    <input
      type="url"
      value={url}
      onChange={(event) => setUrl(event.target.value)}
      placeholder="Paste a product URL..."
      disabled={tracking}
    />
    <button
      type="button"
      onClick={handleTrack}
      disabled={tracking || !url.trim()}
    >
      {tracking ? "Tracking..." : "Track Price"}
    </button>
  </section>
  ```
  This is the vestigial web-scraping control that §R4 explicitly instructs to eliminate or replace.
- **Error Display** (`App.tsx` lines 479–486):
  A basic single error banner: `{error && <div className="error">{error}</div>}`.
- **Grid Container** (`App.tsx` lines 492–502):
  Renders `<PriceGrid>` wrapped in `<section className="grid-container">`.

### 1.2 Frontend Styling & Dependencies Setup
Inspection of `frontend/package.json` (lines 13–20) and CSS files:
- `package.json` lists `"tailwindcss": "^4.3.3"`, `"ag-grid-community": "^36.0.2"`, `"ag-grid-react": "^36.0.2"`, `"react": "^19.2.8"`.
- `frontend/vite.config.ts` does NOT include `@tailwindcss/vite`.
- `frontend/src/index.css` (lines 1–60) defines plain CSS classes (`.app`, `.app-header`, `.toolbar`, `.summary`, `.summary-card`, `.error`, `.grid-container`). It does not import Tailwind directly (`@import "tailwindcss";` is absent).
- Therefore, the new component must be styled using robust semantic CSS classes (or scoped component CSS) that render cleanly regardless of whether Tailwind v4 utility compilation is active, ensuring 100% visual consistency.

### 1.3 Backend Upload API Contract (`POST /api/v1/catalog/imports/upload`)
Inspection of `backend/app/api/v1/catalog.py` (lines 35–98) and `catalog_import_service.py` (lines 33–749):
- **Transport**: `multipart/form-data` with form field `"file": UploadFile`.
- **Query Parameter**: `supplier_name: Optional[str] = Query(default=None)` (defaults to `"Siemens"` in backend).
- **Validation**:
  - File extension must end in `.pdf` (case-insensitive). Non-PDF returns HTTP 400 (`"Only PDF files are supported."`).
  - File must not be empty. Empty file returns HTTP 400 (`"Uploaded PDF is empty."`).
  - File size must be `<= 50 * 1024 * 1024` (50 MB). Exceeding returns HTTP 400 (`"Catalog PDF exceeds the maximum allowed size."`).
- **Response Payload**:
  ```json
  {
    "id": 1,
    "file_name": "Electrical-Installation-Products.pdf",
    "supplier_name": "Siemens",
    "status": "completed",
    "total_rows": 52,
    "imported_rows": 52,
    "failed_rows": 0,
    "created_at": "2026-09-08T07:00:00.123456",
    "completed_at": "2026-09-08T07:00:05.654321"
  }
  ```
- **Backend Statuses**: `"uploaded"`, `"processing"`, `"completed"`, `"completed_with_errors"`, `"failed"`.

### 1.4 Existing Component Inventory
Inspection of `frontend/src/components/`:
- Only `PriceGrid.tsx` is currently present.
- `CatalogUpload.tsx` does NOT exist yet and must be created.

---

## 2. Logic Chain

### 2.1 Component Architecture: `CatalogUpload`
To satisfy §R1 ("Provide a dedicated, intuitive upload component in the frontend header/toolbar"), the component must encapsulate the complete upload workflow:
1. **Interactive File Selection**:
   - Both drag-and-drop zone AND file browser dialog button (`<input type="file" accept=".pdf" />`).
   - Drag-over detection (`dragenter`, `dragover`, `dragleave`, `drop`) with visual highlight (blue dashed border and background tint).
   - Pre-flight client-side validation for file type (`.pdf`) and size (`<= 50MB`), rejecting invalid files immediately with a clear inline alert before making a network request.
2. **Dual-Phase Progress Lifecycle**:
   - *Phase 1: Uploading (0%–100%)*: As the file bytes are transmitted over the wire, `XMLHttpRequest.upload.onprogress` calculates `Math.round((event.loaded / event.total) * 100)`. The progress bar advances smoothly and the status badge displays `Uploading PDF (X%)...`.
   - *Phase 2: Parsing & Coordinate Clustering*: Once byte transmission hits 100%, the backend begins reading PDF coordinates via `pdfplumber` and persisting catalog items. The component transitions status to `Parsing Siemens PDF & Extracting Prices...`, displays an animated indeterminate spinner, and runs an active ticking timer (`Elapsed: X.Xs`).
3. **Terminal Feedback & 4-Tile Metrics Presentation**:
   - When the backend returns HTTP 200:
     - The timer stops.
     - A status badge reflects outcome: `✅ Import Completed Successfully` (if `failed_rows === 0`) or `⚠️ Completed with Errors` (if `failed_rows > 0`).
     - A 4-metric summary feedback card presents:
       - **Imported Rows**: Count of new/updated products (e.g. `52`).
       - **Total Extracted**: Count of parsed PDF line items (e.g. `52`).
       - **Failed Rows**: Count of unparsed or failed rows (e.g. `0`).
       - **Elapsed Time**: Total processing duration (e.g. `3.4s`).
     - Action buttons allow users to either `[ Upload Another Catalog ]` or dismiss/collapse the card.
4. **Auto-Refresh Signaling**:
   - Acceptance Criteria: *"Upon successful upload, the catalog spreadsheet automatically refreshes with the newly imported products."*
   - The component exposes an `onUploadSuccess: (response: CatalogUploadResponse) => void` callback prop.
   - When invoked, parent `App.tsx` immediately triggers a reload of catalog items and categories.

### 2.2 Integration into `App.tsx` Header/Toolbar with Clean Visual Hierarchy
To prevent screen clutter while maintaining high accessibility:
1. **Header Row Organization**:
   - Layout: Flex row `justify-between items-center` with padding `16px 32px`.
   - Left side: Application branding:
     - Title: `Live Spreadsheet`
     - Subtitle / Tagline: `Supplier Catalog Pricing & Quotation Costing`
     - Status Indicator: `Active Supplier: Siemens Betagard`
   - Right side: Quick-action button `[ 📄 + Upload Catalog PDF ]` with badge count of imported items.
2. **Dedicated Upload Zone in Toolbar**:
   - Positioned in the toolbar container directly above the data grid.
   - Features a clean, card-based container (`.catalog-upload-container`).
   - Includes a collapse/expand toggle so users can minimize the upload card once products are loaded, maximizing vertical space for AG Grid viewing.
   - Replaces the vestigial URL scraper input from M1.
3. **Toast / Banner Notification Layer**:
   - A floating toast system in the top-right corner to announce completion (`"Successfully imported 52 Siemens products!"`) or alert on errors, ensuring the user is notified even if scrolled down.

---

## 3. Caveats

1. **Native Fetch vs. XMLHttpRequest for Progress Tracking**:
   - The native browser `fetch()` API does not support body upload progress events. Therefore, `frontend/src/services/catalogApi.ts` must use `XMLHttpRequest` (`xhr.upload.onprogress`) to provide authentic real-time progress percentages (0% to 100%).
2. **Backend Status String Casing**:
   - `PROJECT.md` line 77 illustrates `"status": "COMPLETED"` (uppercase), whereas the actual database model and backend service return lowercase: `"completed"`, `"completed_with_errors"`, `"failed"`. The component must perform case-insensitive normalization: `status.toLowerCase() === "completed"`.
3. **Server Execution Nature**:
   - The backend `/imports/upload` endpoint processes the PDF synchronously before returning the HTTP response. The real-time visual progress reflects byte transmission (0–100%), followed by the backend processing state ("Parsing Siemens PDF...").
4. **Tailwind CSS v4 Configuration**:
   - Because `frontend/src/index.css` does not currently import `@import "tailwindcss";`, styling should be implemented using dedicated CSS classes in `CatalogUpload.css` (or appended to `index.css`) with clean CSS variables and semantic naming to guarantee styling works out of the box without dependency on build-time Tailwind compilation.

---

## 4. Conclusion & Concrete Design Blueprint

### 4.1 Recommended File Structure
```
frontend/src/
├── App.tsx                     # Updated header/toolbar integrating CatalogUpload & auto-refresh
├── components/
│   ├── CatalogUpload.tsx       # NEW: Dedicated drag-and-drop PDF upload component
│   ├── CatalogUpload.css       # NEW: Scoped styling for upload zone, progress bar & metrics
│   └── PriceGrid.tsx           # Existing AG Grid table
├── services/
│   └── catalogApi.ts           # NEW: API client for uploadCatalogPdf, getCatalogItems, etc.
└── types/
    └── catalog.ts              # Existing: CatalogItem, CatalogUploadResponse, etc.
```

---

### 4.2 Complete Component Code Design: `CatalogUpload.tsx`

```tsx
import React, { useState, useRef, useEffect, DragEvent, ChangeEvent } from "react";
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
  | "idle"        // Ready for selection
  | "selected"    // File picked, ready to upload
  | "uploading"   // Sending bytes (0-100%)
  | "parsing"     // Backend coordinate extraction and DB upsert
  | "completed"   // Finished successfully
  | "failed";     // Error occurred

export const CatalogUpload: React.FC<CatalogUploadProps> = ({
  onUploadSuccess,
  onUploadError,
  defaultSupplier = "Siemens",
  className = "",
}) => {
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

  // Active elapsed timer during uploading and parsing
  useEffect(() => {
    if (status === "uploading" || status === "parsing") {
      const startTime = Date.now();
      timerRef.current = window.setInterval(() => {
        setElapsedSeconds(Number(((Date.now() - startTime) / 1000).toFixed(1)));
      }, 100);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [status]);

  // Validate dropped or selected file
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
  };

  // Drag event handlers
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
    // Only reset if leaving the drop container itself
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

  // Execute upload
  const handleStartUpload = async () => {
    if (!file) return;

    setStatus("uploading");
    setProgress(0);
    setErrorMessage(null);

    try {
      const response = await uploadCatalogPdf(
        file,
        supplierName,
        (percent) => {
          setProgress(percent);
          if (percent >= 100) {
            setStatus("parsing");
          }
        }
      );

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

      {/* State: IDLE or DRAGGING */}
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
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
            <div className="catalog-selected-bar">
              <div className="catalog-file-info">
                <span className="catalog-file-badge">PDF</span>
                <span className="catalog-file-name" title={file.name}>{file.name}</span>
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
                <span className="catalog-badge catalog-badge--uploading">
                  <span className="catalog-spinner" /> Uploading PDF ({progress}%)...
                </span>
              ) : (
                <span className="catalog-badge catalog-badge--parsing">
                  <span className="catalog-spinner catalog-spinner--amber" /> Parsing Siemens PDF & Extracting Prices...
                </span>
              )}
            </div>

            <div className="catalog-timer">
              ⏱ Elapsed: <strong>{elapsedSeconds.toFixed(1)}s</strong>
            </div>
          </div>

          {/* Real-time Progress Bar */}
          <div className="catalog-progressbar-track">
            <div
              className={`catalog-progressbar-fill ${status === "parsing" ? "catalog-progressbar-fill--pulse" : ""}`}
              style={{ width: `${Math.max(5, progress)}%` }}
            />
          </div>

          <div className="catalog-progress-footer">
            <span className="catalog-progress-filename">{file?.name}</span>
            <span className="catalog-progress-phase">
              {status === "uploading" ? `${progress}% transmitted` : "Analyzing coordinate clusters & saving items..."}
            </span>
          </div>
        </div>
      )}

      {/* State: COMPLETED (Summary Feedback Presentation) */}
      {status === "completed" && result && (
        <div className="catalog-summary-section" data-testid="catalog-summary-section">
          <div className="catalog-summary-header">
            <div className="catalog-summary-title">
              <span className="catalog-badge catalog-badge--completed">
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
            >
              Upload Another Catalog
            </button>
          </div>

          {/* 4-Tile Feedback Metric Grid */}
          <div className="catalog-metrics-grid">
            <div className="catalog-metric-card catalog-metric-card--success">
              <span className="catalog-metric-label">Imported Rows</span>
              <strong className="catalog-metric-value">{result.imported_rows}</strong>
              <span className="catalog-metric-sub">Added to catalog</span>
            </div>

            <div className="catalog-metric-card">
              <span className="catalog-metric-label">Total Extracted</span>
              <strong className="catalog-metric-value">{result.total_rows}</strong>
              <span className="catalog-metric-sub">PDF line items</span>
            </div>

            <div className={`catalog-metric-card ${result.failed_rows > 0 ? "catalog-metric-card--warning" : ""}`}>
              <span className="catalog-metric-label">Failed Rows</span>
              <strong className="catalog-metric-value">{result.failed_rows}</strong>
              <span className="catalog-metric-sub">Parse errors</span>
            </div>

            <div className="catalog-metric-card">
              <span className="catalog-metric-label">Elapsed Time</span>
              <strong className="catalog-metric-value">{elapsedSeconds.toFixed(1)}s</strong>
              <span className="catalog-metric-sub">End-to-end duration</span>
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
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
};
```

---

### 4.3 Component Stylesheet: `CatalogUpload.css`

```css
/* CatalogUpload.css — Polished Modern Styling */

.catalog-upload-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  margin-bottom: 20px;
  transition: all 0.2s ease-in-out;
}

/* Drag-and-Drop Zone */
.catalog-dropzone {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border: 2px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.2s ease;
}

.catalog-dropzone:hover {
  border-color: #3b82f6;
  background: #f0f7ff;
}

.catalog-dropzone--active {
  border-color: #2563eb;
  background: #e0f2fe;
  transform: scale(1.005);
}

.catalog-dropzone-icon {
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.catalog-dropzone-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.catalog-dropzone-primary {
  font-size: 14px;
  color: #1e293b;
}

.catalog-dropzone-secondary {
  font-size: 12px;
  color: #64748b;
}

/* Selected File Bar */
.catalog-selected-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 14px;
  background: #f1f5f9;
  border-radius: 6px;
}

.catalog-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.catalog-file-badge {
  background: #ef4444;
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.catalog-file-name {
  font-weight: 600;
  color: #0f172a;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.catalog-file-size {
  color: #64748b;
}

.catalog-supplier-select {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #475569;
}

.catalog-supplier-input {
  padding: 4px 8px;
  font-size: 13px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  width: 110px;
}

.catalog-action-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Buttons */
.catalog-btn {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  border: none;
  transition: all 0.15s ease;
}

.catalog-btn--primary {
  background: #2563eb;
  color: #ffffff;
}

.catalog-btn--primary:hover {
  background: #1d4ed8;
}

.catalog-btn--secondary {
  background: #e2e8f0;
  color: #475569;
  padding: 8px 10px;
}

.catalog-btn--secondary:hover {
  background: #cbd5e1;
}

.catalog-btn--outline {
  background: transparent;
  border: 1px solid #cbd5e1;
  color: #334155;
}

.catalog-btn--outline:hover {
  background: #f8fafc;
  border-color: #94a3b8;
}

/* Badges & Status */
.catalog-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.catalog-badge--uploading {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.catalog-badge--parsing {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.catalog-badge--completed {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.catalog-badge--failed {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

/* Spinner */
.catalog-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #93c5fd;
  border-top-color: #1e40af;
  border-radius: 50%;
  animation: catalog-spin 0.8s linear infinite;
}

.catalog-spinner--amber {
  border-color: #fcd34d;
  border-top-color: #92400e;
}

@keyframes catalog-spin {
  to { transform: rotate(360deg); }
}

/* Real-time Progress Bar */
.catalog-progress-section {
  padding: 4px 0;
}

.catalog-status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.catalog-timer {
  font-size: 12px;
  color: #64748b;
}

.catalog-progressbar-track {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.catalog-progressbar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  transition: width 0.2s ease;
}

.catalog-progressbar-fill--pulse {
  animation: catalog-pulse 1.5s ease-in-out infinite;
}

@keyframes catalog-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.catalog-progress-footer {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  margin-top: 6px;
}

/* Summary Feedback Grid */
.catalog-summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
}

.catalog-summary-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.catalog-summary-meta {
  font-size: 12px;
  color: #64748b;
}

.catalog-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}

.catalog-metric-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
}

.catalog-metric-label {
  font-size: 11px;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.catalog-metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
  margin: 4px 0 2px;
}

.catalog-metric-card--success .catalog-metric-value {
  color: #16a34a;
}

.catalog-metric-card--warning .catalog-metric-value {
  color: #dc2626;
}

.catalog-metric-sub {
  font-size: 11px;
  color: #94a3b8;
}

.catalog-autorefresh-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #059669;
  font-weight: 500;
}

.catalog-pulse-dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.3);
}

/* Alert Notification */
.catalog-alert {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 6px;
  margin-top: 12px;
  font-size: 13px;
}

.catalog-alert--error {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  color: #991b1b;
}

.catalog-alert-content {
  flex: 1;
}

.catalog-alert-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 14px;
  cursor: pointer;
}
```

---

### 4.4 Header & Toolbar Integration in `frontend/src/App.tsx`

Below is the concrete blueprint showing how `CatalogUpload` integrates into `App.tsx`:

```tsx
import { useEffect, useState } from "react";
import PriceGrid from "./components/PriceGrid";
import { CatalogUpload } from "./components/CatalogUpload";
import type { CatalogUploadResponse } from "./types/catalog";
import type { ProductRow } from "./types/price";
import { getProducts } from "./services/productApi";
import { productToRow } from "./utils/productMapper";

function App() {
  const [rows, setRows] = useState<ProductRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Auto-refresh trigger counter incremented upon successful catalog PDF upload
  const [catalogVersion, setCatalogVersion] = useState(0);

  // Optional toast state for top-level notifications
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // --------------------------------------------------
  // LOAD PRODUCTS (refreshes on catalogVersion change)
  // --------------------------------------------------
  useEffect(() => {
    async function loadProducts() {
      try {
        setLoading(true);
        setError(null);

        const products = await getProducts();
        setRows(products.map(productToRow));
      } catch (err) {
        console.error(err);
        setError(err instanceof Error ? err.message : "Failed to load products");
      } finally {
        setLoading(false);
      }
    }

    loadProducts();
  }, [catalogVersion]);

  // Handle successful upload from CatalogUpload component
  const handleCatalogUploadSuccess = (response: CatalogUploadResponse) => {
    // 1. Trigger catalog spreadsheet auto-refresh immediately
    setCatalogVersion((v) => v + 1);

    // 2. Display brief success toast
    setToast({
      message: `Successfully imported ${response.imported_rows} catalog rows from ${response.file_name}!`,
      type: "success",
    });

    setTimeout(() => {
      setToast(null);
    }, 5000);
  };

  return (
    <main className="app">
      {/* -------------------------------------------- */}
      {/* HEADER: Clean visual hierarchy               */}
      {/* -------------------------------------------- */}
      <header className="app-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span>Live Spreadsheet</span>
            <span style={{ fontSize: "12px", background: "#e0f2fe", color: "#0369a1", padding: "2px 8px", borderRadius: "12px", fontWeight: 600 }}>
              Catalog & Quotation
            </span>
          </h1>
          <p style={{ color: "#64748b", margin: 0, fontSize: "14px" }}>
            Manufacturer Catalog Pricing & Interactive Quotation Costing
          </p>
        </div>

        {/* Global Toast if active */}
        {toast && (
          <div style={{
            background: toast.type === "success" ? "#dcfce7" : "#fee2e2",
            color: toast.type === "success" ? "#166534" : "#991b1b",
            border: `1px solid ${toast.type === "success" ? "#86efac" : "#fca5a5"}`,
            padding: "6px 14px",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 500
          }}>
            {toast.message}
          </div>
        )}
      </header>

      {/* -------------------------------------------- */}
      {/* TOOLBAR / CATALOG UPLOAD INTEGRATION         */}
      {/* -------------------------------------------- */}
      <div style={{ padding: "16px 32px 0" }}>
        {/* Dedicated PDF Catalog Upload Component */}
        <CatalogUpload
          defaultSupplier="Siemens"
          onUploadSuccess={handleCatalogUploadSuccess}
          onUploadError={(err) => setError(err.message)}
        />
      </div>

      {/* -------------------------------------------- */}
      {/* GRID CONTAINER                               */}
      {/* -------------------------------------------- */}
      <section className="grid-container">
        {loading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "#64748b" }}>
            Loading catalog data...
          </div>
        ) : (
          <PriceGrid
            rows={rows}
            onRowsChange={setRows}
            onRefresh={() => setCatalogVersion((v) => v + 1)}
            onDelete={(id) => setRows((r) => r.filter((row) => row.id !== id))}
          />
        )}
      </section>
    </main>
  );
}

export default App;
```

---

## 5. Verification Method

### 5.1 Static Verification & TypeScript Build
Verify that the TypeScript types, interfaces, and component compiles cleanly with zero diagnostics:
```powershell
npm --prefix frontend run build
```

### 5.2 Unit & Component Vitest Suite
A new test file `frontend/src/tests/catalogUpload.test.ts` (or `CatalogUpload.test.tsx`) can be created to verify:
1. Drag-and-drop event handling and file selection.
2. File extension and size boundaries (rejecting `.txt` or 0-byte files).
3. Progression states (`uploading` -> `parsing` -> `completed`).
4. Rendering of the 4-tile summary cards (`imported_rows`, `total_rows`, `failed_rows`, `elapsedTime`).
5. Invocation of `onUploadSuccess` prop with backend payload.

Run tests:
```powershell
npm --prefix frontend run test
```

### 5.3 Backend Alignment Verification
Verify that backend tests for upload, parser, and status tracking continue passing 100%:
```powershell
pytest backend/app/tests/e2e/test_tier1_features.py -k "test_f1 or test_f2 or test_f3" -v
```

### 5.4 Invalidation Conditions
- Changes to backend `POST /api/v1/catalog/imports/upload` parameter naming or response fields.
- Switching from synchronous HTTP upload response to asynchronous task polling (e.g. Celery returning HTTP 202).
- Migration of the frontend to an external UI library (e.g. Radix UI or Material UI) that alters class names.
