from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.cart import Cart, CartItem
from models.user import User
from schemas.cart import CartItemCreate, CartItemUpdate, CartOut, CartItemOut  # ← Добавлен CartItemOut
from utils.auth import get_current_active_user

router = APIRouter(prefix="/cart", tags=["cart"])

@router.post("/add", response_model=CartItemOut)
async def add_to_cart(
    item_: CartItemCreate,  # ← Исправлено: item_data → item_
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Найдём корзину пользователя
    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id)
    )
    cart = cart_result.scalars().first()

    if not cart:
        # Создаём корзину, если нет
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    # Проверим, есть ли уже такой товар в корзине
    existing_item_result = await db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == item_.product_id  # ← Исправлено: item_data.product_id → item_.product_id
        )
    )
    existing_item = existing_item_result.scalars().first()

    if existing_item:
        # Обновим количество
        existing_item.quantity += item_.quantity  # ← Исправлено: item_data.quantity → item_.quantity
    else:
        # Создадим новый элемент
        new_item = CartItem(
            cart_id=cart.id,
            product_id=item_.product_id,  # ← Исправлено: item_data.product_id → item_.product_id
            quantity=item_.quantity  # ← Исправлено: item_data.quantity → item_.quantity
        )
        db.add(new_item)

    await db.commit()

    # Вернём созданный/обновлённый элемент
    final_item = existing_item if existing_item else new_item
    return final_item

@router.put("/update/{item_id}", response_model=CartItemOut)
async def update_cart_item(
    item_id: int,
    item_: CartItemUpdate,  # ← Исправлено: item_data → item_
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Найдём элемент корзины
    result = await db.execute(
        select(CartItem)
        .join(Cart)
        .where(CartItem.id == item_id, Cart.user_id == current_user.id)
    )
    item = result.scalars().first()

    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    item.quantity = item_.quantity  # ← Исправлено: item_data.quantity → item_.quantity
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/remove/{item_id}")
async def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Найдём элемент корзины
    result = await db.execute(
        select(CartItem)
        .join(Cart)
        .where(CartItem.id == item_id, Cart.user_id == current_user.id)
    )
    item = result.scalars().first()

    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await db.delete(item)
    await db.commit()
    return {"message": "Item removed from cart"}

@router.get("/", response_model=CartOut)
async def get_cart(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Найдём корзину пользователя
    cart_result = await db.execute(
        select(Cart).where(Cart.user_id == current_user.id)
    )
    cart = cart_result.scalars().first()

    if not cart:
        # Если корзины нет — вернём пустую
        return {"id": None, "user_id": current_user.id, "items": []}

    # Найдём товары в корзине
    items_result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id)
    )
    items = items_result.scalars().all()

    return {"id": cart.id, "user_id": current_user.id, "items": items}