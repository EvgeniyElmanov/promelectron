from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.models.cart import Cart, CartItem
from server.app.models.user import User
from server.app.schemas.cart import CartItemCreate, CartItemUpdate


class CartService:
    @staticmethod
    async def add_to_cart(
        item_data: CartItemCreate, current_user: User, db: AsyncSession
    ) -> CartItem:
        cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user.id))
        cart = cart_result.scalars().first()

        if not cart:
            cart = Cart(user_id=current_user.id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)

        existing_item_result = await db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id, CartItem.product_id == item_data.product_id
            )
        )
        existing_item = existing_item_result.scalars().first()

        if existing_item:
            existing_item.quantity += item_data.quantity
            final_item = existing_item
        else:
            final_item = CartItem(
                cart_id=cart.id, product_id=item_data.product_id, quantity=item_data.quantity
            )
            db.add(final_item)

        await db.commit()
        await db.refresh(final_item)
        return final_item

    @staticmethod
    async def update_cart_item(
        item_id: int, item_data: CartItemUpdate, current_user: User, db: AsyncSession
    ) -> CartItem:
        result = await db.execute(
            select(CartItem).join(Cart).where(CartItem.id == item_id, Cart.user_id == current_user.id)
        )
        item = result.scalars().first()

        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        item.quantity = item_data.quantity
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def remove_from_cart(item_id: int, current_user: User, db: AsyncSession) -> dict[str, str]:
        result = await db.execute(
            select(CartItem).join(Cart).where(CartItem.id == item_id, Cart.user_id == current_user.id)
        )
        item = result.scalars().first()

        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        await db.delete(item)
        await db.commit()
        return {"message": "Item removed from cart"}

    @staticmethod
    async def get_cart(current_user: User, db: AsyncSession) -> dict[str, object]:
        cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user.id))
        cart = cart_result.scalars().first()

        if not cart:
            return {"id": 0, "user_id": current_user.id, "items": []}

        items_result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
        items = list(items_result.scalars().all())
        return {"id": cart.id, "user_id": current_user.id, "items": items}
