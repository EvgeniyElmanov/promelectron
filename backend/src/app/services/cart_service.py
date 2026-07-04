from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.models.cart import Cart, CartItem
from src.app.models.product import Product
from src.app.models.recipient import Recipient
from src.app.models.user import User, UserAddress
from src.app.schemas.cart import CartItemCreate, CartItemSelect, CartItemUpdate, CartMergeItem


class CartService:
    @staticmethod
    async def _validate_product_and_stock(
        product_id: int, requested_quantity: int, db: AsyncSession, existing_quantity: int = 0
    ) -> None:
        product_result = await db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalars().first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {product_id} is not active")
        total = requested_quantity + existing_quantity
        if total > product.stock:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for product {product_id}. "
                       f"Available: {product.stock}, requested: {total}",
            )

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

        existing_quantity = existing_item.quantity if existing_item else 0
        await CartService._validate_product_and_stock(
            item_data.product_id, item_data.quantity, db, existing_quantity
        )

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

        await CartService._validate_product_and_stock(
            item.product_id, item_data.quantity, db, existing_quantity=0
        )

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
    async def remove_cart_items_by_ids(cart_item_ids: list[int], db: AsyncSession) -> None:
        if not cart_item_ids:
            return
        await db.execute(
            delete(CartItem).where(CartItem.id.in_(cart_item_ids))
        )
        await db.commit()

    @staticmethod
    async def set_selected(
        item_id: int, item_data: CartItemSelect, current_user: User, db: AsyncSession
    ) -> CartItem:
        result = await db.execute(
            select(CartItem).join(Cart).where(CartItem.id == item_id, Cart.user_id == current_user.id)
        )
        item = result.scalars().first()

        if not item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        item.selected = item_data.selected
        await db.commit()

        result = await db.execute(
            select(CartItem)
            .where(CartItem.id == item.id)
            .options(selectinload(CartItem.product))
        )
        return result.scalars().first()

    @staticmethod
    async def select_all(current_user: User, db: AsyncSession) -> dict[str, object]:
        cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user.id))
        cart = cart_result.scalars().first()

        if cart:
            await db.execute(
                update(CartItem)
                .where(CartItem.cart_id == cart.id)
                .values(selected=True)
            )
            await db.commit()

        return await CartService.get_cart(current_user=current_user, db=db)

    @staticmethod
    async def deselect_all(current_user: User, db: AsyncSession) -> dict[str, object]:
        cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user.id))
        cart = cart_result.scalars().first()

        if cart:
            await db.execute(
                update(CartItem)
                .where(CartItem.cart_id == cart.id)
                .values(selected=False)
            )
            await db.commit()

        return await CartService.get_cart(current_user=current_user, db=db)

    @staticmethod
    async def get_cart(current_user: User, db: AsyncSession) -> dict[str, object]:
        cart_result = await db.execute(select(Cart).where(Cart.user_id == current_user.id))
        cart = cart_result.scalars().first()

        default_recipient_result = await db.execute(
            select(Recipient).where(
                Recipient.user_id == current_user.id, Recipient.is_default.is_(True)
            )
        )
        default_recipient = default_recipient_result.scalars().first()

        default_address_result = await db.execute(
            select(UserAddress).where(
                UserAddress.user_id == current_user.id, UserAddress.is_default.is_(True)
            )
        )
        default_address = default_address_result.scalars().first()

        if not cart:
            return {
                "id": 0,
                "user_id": current_user.id,
                "items": [],
                "default_recipient": default_recipient,
                "default_address": default_address,
            }

        items_result = await db.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .options(selectinload(CartItem.product))
        )
        items = list(items_result.scalars().all())
        return {
            "id": cart.id,
            "user_id": current_user.id,
            "items": items,
            "default_recipient": default_recipient,
            "default_address": default_address,
        }

    @staticmethod
    async def merge_cart(
        items_data: list[CartMergeItem], current_user: User, db: AsyncSession
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
            existing_quantity = existing_item.quantity if existing_item else 0
            await CartService._validate_product_and_stock(
                item_data.product_id, item_data.quantity, db, existing_quantity
            )
            if existing_item:
                existing_item.quantity += item_data.quantity
            else:
                new_item = CartItem(
                    cart_id=cart.id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    selected=item_data.selected,
                )
                db.add(new_item)

        await db.commit()

        return await CartService.get_cart(current_user=current_user, db=db)
