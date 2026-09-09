from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

app = FastAPI(title="pricing_webapp")  # title will be updated at startup


@app.on_event("startup")
async def _apply_settings_on_startup() -> None:
    """
    Delay construction of Settings until startup so importing this module
    (e.g., during pytest collection) does not require environment variables
    to be present.
    """
    settings = get_settings()
    app.title = settings.app_name

    # Add CORS middleware using runtime settings
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
