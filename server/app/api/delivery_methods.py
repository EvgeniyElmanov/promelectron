from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import get_db
from server.app.schemas.delivery_method import DeliveryMethodCreate, DeliveryMethodOut, DeliveryMethodUpdate
from server.app.services.delivery_method_service import DeliveryMethodService
from server.app.utils.auth import get_current_active_admin

router = APIRouter(prefix="/delivery-methods", tags=["delivery-methods"])


@router.get("/", response_model=List[DeliveryMethodOut])
async def get_delivery_methods(db: AsyncSession = Depends(get_db)):
    return await DeliveryMethodService.get_methods(db=db)


@router.post("/", response_model=DeliveryMethodOut)
async def create_delivery_method(
    data: DeliveryMethodCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_admin),
):
    return await DeliveryMethodService.create_method(data=data, db=db)


@router.put("/{method_id}", response_model=DeliveryMethodOut)
async def update_delivery_method(
    method_id: int,
    data: DeliveryMethodUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_admin),
):
    return await DeliveryMethodService.update_method(method_id=method_id, data=data, db=db)


@router.delete("/{method_id}")
async def delete_delivery_method(
    method_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_admin),
):
    return await DeliveryMethodService.delete_method(method_id=method_id, db=db)
