from fastapi import APIRouter

from app.api.v1.prices import router as prices_router
from app.api.v1.products import router as products_router


api_router = APIRouter()

api_router.include_router(prices_router)
api_router.include_router(products_router)