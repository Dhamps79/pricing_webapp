# Pricing Webapp
# Live Spreadsheet (Pricing Webapp)

A full-stack product pricing and catalog management platform.
A full-stack product pricing, catalog management, and quotation builder platform.

## Stack
---

### Backend
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- HTTPX
- BeautifulSoup
- Pytest
## 🚀 1-Click Quickstart (For Non-Technical Users)

### Frontend
- React
- TypeScript
- Vite
- AG Grid
- Vitest
You do **not** need to install PostgreSQL or Docker to use this app locally. It comes ready out of the box with an embedded clean database!

## Features
### On Windows:
1. Double-click **`run_app.bat`** in this folder.
2. The application will start and automatically open in your default browser at:
   **`http://localhost:8000`**
3. That's it! You can start uploading catalog PDFs, searching items, creating costing sheets, and exporting quotations.

- Product management
- Product search and filtering
- Live price tracking
- Price history
- Price trend detection
- Multiple pricing sources
- Siemens catalog import
- PDF parsing
- Costing sheets
- Spreadsheet-style editing
- Quantity and target-price tracking
- Product notes
- REST API
- Docker
- CI
### On Mac / Linux / Terminal:
```bash
python run_local.py
```
This will automatically launch the server and open your browser at `http://localhost:8000`.

## Local development
---

### Backend
## ☁️ Deploying to Render

```bash
cd backend
You can deploy this application directly to Render as a Docker Web Service:

python -m venv .venv
1. Push this repository to GitHub or GitLab.
2. Log in to [Render.com](https://render.com) and click **New +** -> **Web Service**.
3. Select your repository.
4. Render will automatically detect the **`Dockerfile`** (multi-stage build that compiles React and serves FastAPI).
5. Choose the **Free** instance type.
6. Click **Deploy Web Service**!
   - Render will build the frontend assets, set up the backend, and provide you with a public shareable URL (e.g., `https://live-spreadsheet.onrender.com`).

# Windows
.venv\Scripts\activate
*(Optional)*: If you wish to use Render's managed PostgreSQL database instead of the built-in SQLite database, simply add the `DATABASE_URL` environment variable under your Web Service Settings.

pip install -r requirements.txt
---

alembic upgrade head
## 🛠️ Developer Architecture

uvicorn app.main:app --reload
- **Backend**: FastAPI, SQLAlchemy, SQLite (default) / PostgreSQL, PyPDFium2 / PDFPlumber
- **Frontend**: React 19, TypeScript, Vite, AG Grid, Tailwind CSS
- **Packaging**: FastAPI automatically serves built frontend assets from `frontend/dist/` or `static/` with full SPA HTML5 fallback.