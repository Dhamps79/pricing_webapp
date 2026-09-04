from fastapi import APIRouter

from app.api.v1.catalog import router as catalog_router
from app.api.v1.costing import router as costing_router
from app.api.v1.prices import router as prices_router
from app.api.v1.products import router as products_router
from app.api.v1.health import router as health_router


api_router = APIRouter()

api_router.include_router(prices_router)
api_router.include_router(products_router)
api_router.include_router(catalog_router)
api_router.include_router(costing_router)
api_router.include_router(health_router)