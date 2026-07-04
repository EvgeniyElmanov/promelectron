from fastapi import APIRouter, Depends, Request
from src.app.utils.rate_limiter import conditional_limit
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import get_db
from src.app.models.user import User
from src.app.schemas.cart import (
    CartItemCreate,
    CartItemOut,
    CartItemSelect,
    CartItemUpdate,
    CartMergeRequest,
    CartOut,
)
from src.app.services.cart_service import CartService
from src.app.utils.auth import get_current_active_user

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/add", response_model=CartItemOut)
@conditional_limit("20/minute")
async def add_to_cart(request: Request,
    item_: CartItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.add_to_cart(item_data=item_, current_user=current_user, db=db)


@router.put("/update/{item_id}", response_model=CartItemOut)
async def update_cart_item(
    item_id: int,
    item_: CartItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.update_cart_item(
        item_id=item_id, item_data=item_, current_user=current_user, db=db
    )


@router.delete("/remove/{item_id}")
async def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.remove_from_cart(item_id=item_id, current_user=current_user, db=db)


@router.get("/", response_model=CartOut)
async def get_cart(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.get_cart(current_user=current_user, db=db)


@router.patch("/select/{item_id}/", response_model=CartItemOut)
async def set_cart_item_selected(
    item_id: int,
    item_: CartItemSelect,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.set_selected(
        item_id=item_id, item_data=item_, current_user=current_user, db=db
    )


@router.post("/select-all/", response_model=CartOut)
async def select_all(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.select_all(current_user=current_user, db=db)


@router.post("/deselect-all/", response_model=CartOut)
async def deselect_all(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.deselect_all(current_user=current_user, db=db)


@router.post("/merge", response_model=CartOut)
async def merge_cart(
    items_: CartMergeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.merge_cart(
        items_data=items_.items, current_user=current_user, db=db
    )

