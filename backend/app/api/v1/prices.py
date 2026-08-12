from fastapi import APIRouter, HTTPException

from app.schemas.price import PriceLookupRequest, PriceLookupResponse
from app.services.price_service import lookup_price

router = APIRouter()


@router.post("/lookup", response_model=PriceLookupResponse)
async def lookup(request: PriceLookupRequest) -> PriceLookupResponse:
    try:
        return await lookup_price(str(request.url))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to read price from source") from exc
