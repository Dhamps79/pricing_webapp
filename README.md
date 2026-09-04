# Pricing Webapp

A full-stack product pricing and catalog management platform.

## Stack

### Backend
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- HTTPX
- BeautifulSoup
- Pytest

### Frontend
- React
- TypeScript
- Vite
- AG Grid
- Vitest

## Features

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

## Local development

### Backend

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --reload