from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.database.base import Base
from app.database.engine import engine
import app.database.models  # noqa: F401


# Ensure all tables exist in database (creates SQLite file and schema automatically on import and startup)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# Add CORS middleware at instantiation time (Starlette requires middleware before startup)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    api_router,
    prefix="/api/v1",
)

# Serve built frontend if exists
# In development or production, frontend is located relative to backend or repo root
potential_dist_paths = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path(__file__).resolve().parent.parent / "static",
    Path("static"),
    Path("../frontend/dist"),
]

dist_path = None
for p in potential_dist_paths:
    if p.exists() and (p / "index.html").exists():
        dist_path = p
        break

if dist_path:
    # Mount assets folder
    assets_path = dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

    # Serve index.html for root and any non-api paths (SPA fallback)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = dist_path / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")

