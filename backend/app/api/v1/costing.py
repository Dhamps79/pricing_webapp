from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.sessions import get_db
from app.services.costing_service import (
    add_product_to_sheet,
    add_products_batch_to_sheet,
    create_sheet,
    delete_sheet,
    export_sheet_to_csv,
    get_sheet,
    list_sheets,
    remove_line,
    update_line,
    update_sheet,
)


router = APIRouter(
    prefix="/costing-sheets",
    tags=["Costing Sheets"],
)


class CostingSheetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    customer_name: str | None = None
    notes: str | None = None
    discount_percent: Decimal = Decimal("0")


class CostingSheetUpdate(BaseModel):
    title: str | None = None
    customer_name: str | None = None
    notes: str | None = None
    discount_percent: Decimal | None = None


class CostingLineCreate(BaseModel):
    product_id: int
    quantity: Decimal = Decimal("1")
    sell_price: Decimal | None = None
    discount_percent: Decimal = Decimal("0")
    notes: str | None = None


class CostingLineUpdate(BaseModel):
    quantity: Decimal | None = None
    sell_price: Decimal | None = None
    discount_percent: Decimal | None = None
    notes: str | None = None


class CostingBatchLinesCreate(BaseModel):
    product_ids: list[int] = Field(min_length=1)
    quantity: Decimal = Decimal("1")



@router.get("")
def get_costing_sheets(
    db: Session = Depends(get_db),
):
    return list_sheets(db)


@router.post("")
def create_costing_sheet(
    payload: CostingSheetCreate,
    db: Session = Depends(get_db),
):
    return create_sheet(
        db=db,
        title=payload.title,
        customer_name=payload.customer_name,
        notes=payload.notes,
        discount_percent=payload.discount_percent,
    )


@router.get("/{sheet_id}")
def get_costing_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
):
    sheet = get_sheet(db, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Costing sheet not found")
    return sheet


@router.patch("/{sheet_id}")
def patch_costing_sheet(
    sheet_id: int,
    payload: CostingSheetUpdate,
    db: Session = Depends(get_db),
):
    sheet = update_sheet(
        db=db,
        sheet_id=sheet_id,
        title=payload.title,
        customer_name=payload.customer_name,
        notes=payload.notes,
        discount_percent=payload.discount_percent,
    )
    if sheet is None:
        raise HTTPException(status_code=404, detail="Costing sheet not found")
    return sheet


@router.delete("/{sheet_id}")
def delete_costing_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
):
    deleted = delete_sheet(db, sheet_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Costing sheet not found")
    return {"message": "Costing sheet deleted", "id": sheet_id}


@router.post("/{sheet_id}/lines")
def add_line(
    sheet_id: int,
    payload: CostingLineCreate,
    db: Session = Depends(get_db),
):
    sheet = add_product_to_sheet(
        db=db,
        sheet_id=sheet_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        sell_price=payload.sell_price,
        discount_percent=payload.discount_percent,
        notes=payload.notes,
    )
    if sheet is None:
        raise HTTPException(
            status_code=404,
            detail="Costing sheet or product not found",
        )
    return sheet


@router.patch("/{sheet_id}/lines/{line_id}")
def patch_line(
    sheet_id: int,
    line_id: int,
    payload: CostingLineUpdate,
    db: Session = Depends(get_db),
):
    sheet = update_line(
        db=db,
        sheet_id=sheet_id,
        line_id=line_id,
        quantity=payload.quantity,
        sell_price=payload.sell_price,
        discount_percent=payload.discount_percent,
        notes=payload.notes,
    )
    if sheet is None:
        raise HTTPException(status_code=404, detail="Line not found")
    return sheet


@router.delete("/{sheet_id}/lines/{line_id}")
def delete_line(
    sheet_id: int,
    line_id: int,
    db: Session = Depends(get_db),
):
    sheet = remove_line(db, sheet_id, line_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Line not found")
    return sheet


@router.post("/{sheet_id}/lines/batch")
def add_lines_batch(
    sheet_id: int,
    payload: CostingBatchLinesCreate,
    db: Session = Depends(get_db),
):
    sheet = add_products_batch_to_sheet(
        db=db,
        sheet_id=sheet_id,
        product_ids=payload.product_ids,
        quantity=payload.quantity,
    )
    if sheet is None:
        raise HTTPException(
            status_code=404,
            detail="Costing sheet not found or empty product IDs",
        )
    return sheet


@router.get("/{sheet_id}/export/csv")
def export_costing_sheet_csv(
    sheet_id: int,
    db: Session = Depends(get_db),
):
    sheet = get_sheet(db, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Costing sheet not found")

    csv_data = export_sheet_to_csv(sheet)
    filename = f"costing_sheet_{sheet_id}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

