# Live Spreadsheet (Pricing Webapp)

A complete, full-stack electrical catalog pricing management and quotation builder application.
Runs seamlessly both **offline on a local PC** and **online via cloud platforms like Render**.

---

## 🚀 1-Click Quickstart for Local PC (Offline, No Internet Needed)

You do **not** need Docker, PostgreSQL, or npm installed to run this application on your computer. It starts completely clean with zero prior data and stores everything in a local embedded SQLite database.

### On Windows:
1. Double-click **`run_app.bat`** in the application folder.
2. The server starts and automatically opens in your default browser at:
   **`http://localhost:8000`**
3. Upload PDF catalogs (e.g., Siemens Betagard), search items, create costing sheets, and calculate quotes with real-time discounts!

*To exit anytime: Close the terminal window or press `Ctrl + C`.*

### On macOS / Linux:
```bash
python run_local.py
```
This automatically launches the server and opens your browser to `http://localhost:8000`.

### Setting up a New PC:
If Python dependencies are not yet installed on a new computer:
1. Double-click **`setup_offline_env.bat`** (or run `pip install -r backend/requirements.txt`).
2. Double-click **`run_app.bat`**.

---

## 📦 Creating a Shareable Download Package

To bundle this application into a clean, standalone ZIP file that you can share with non-technical users:

```bash
python create_offline_package.py
```

This creates **`LiveSpreadsheet-Offline-App.zip`**:
- Includes the 1-click launchers (`run_app.bat`, `run_local.py`, `setup_offline_env.bat`).
- Includes user instructions (`INSTRUCTIONS.txt`).
- Includes the pre-compiled React frontend (`frontend/dist/`).
- Includes the full FastAPI backend.
- Automatically excludes git files, development caches, and local databases to guarantee a clean initial state.

---

## ☁️ Deploying to Render

You can also deploy this application to Render as a Docker Web Service:

1. Push this repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com/), click **New +** -> **Web Service**.
3. Select your repository.
4. Render automatically uses the multi-stage **`Dockerfile`** to compile the React frontend and launch FastAPI.
5. Select the **Free** instance type and click **Deploy**.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite (default for local) / PostgreSQL, PyPDFium2, PDFPlumber
- **Frontend**: React 19, TypeScript, Vite, AG Grid Community, Tailwind CSS
- **Architecture**: Single-port local deployment where FastAPI serves API endpoints under `/api/v1/` and the SPA frontend from `frontend/dist/`.