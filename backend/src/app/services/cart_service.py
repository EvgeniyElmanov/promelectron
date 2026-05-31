from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.models.cart import Cart, CartItem
from src.app.models.user import User
from src.app.schemas.cart import CartItemCreate, CartItemUpdate


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

        result = await db.execute(
            select(CartItem)
            .where(CartItem.id == final_item.id)
            .options(selectinload(CartItem.product))
        )
        return result.scalars().first()

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

        result = await db.execute(
            select(CartItem)
            .where(CartItem.id == item.id)
            .options(selectinload(CartItem.product))
        )
        return result.scalars().first()

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

        items_result = await db.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .options(selectinload(CartItem.product))
        )
        items = list(items_result.scalars().all())
        return {"id": cart.id, "user_id": current_user.id, "items": items}

    @staticmethod
    async def merge_cart(
        items_data: list[CartItemCreate], current_user: User, db: AsyncSession
    ) -> dict[str, object]:
        cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user.id))
        cart = cart_result.scalars().first()

        if not cart:
            cart = Cart(user_id=current_user.id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)

        for item_data in items_data:
            existing_item_result = await db.execute(
                select(CartItem).where(
                    CartItem.cart_id == cart.id,
                    CartItem.product_id == item_data.product_id,
                )
            )
            existing_item = existing_item_result.scalars().first()
            if existing_item:
                existing_item.quantity += item_data.quantity
            else:
                new_item = CartItem(
                    cart_id=cart.id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                )
                db.add(new_item)

        await db.commit()

        items_result = await db.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .options(selectinload(CartItem.product))
        )
        items = list(items_result.scalars().all())
        return {"id": cart.id, "user_id": current_user.id, "items": items}
