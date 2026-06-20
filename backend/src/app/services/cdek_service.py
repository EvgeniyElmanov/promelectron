import json
import logging
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.core.constants import PVZ_TYPE_WHITELIST
from src.app.core.redis_client import RedisClient
from src.app.models.order import Order, OrderItem
from src.app.models.product import Product
from src.app.models.supplier import Supplier
from src.app.services.cdek_client import CdekAPIError, CdekClient

logger = logging.getLogger(__name__)

PVZ_CITY_CACHE_TTL = 86400
PVZ_LIST_CACHE_TTL = 21600


class CdekService:
    DEFAULT_WEIGHT_GRAMS = 1000
    DEFAULT_DIMENSION_CM = 10

    @staticmethod
    def _phone(phone: str | None) -> str:
        if not phone:
            return "+70000000000"
        cleaned = "".join(c for c in phone if c.isdigit())
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = "7" + cleaned[1:]
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned

    @staticmethod
    def _format_address_string(order: Order) -> str:
        if order.cdek_delivery_point:
            return f"ПВЗ {order.cdek_delivery_point}"
        if order.cdek_to_location:
            return order.cdek_to_location.get("address", "")
        return ""

    @staticmethod
    async def _build_packages(order: Order, db: AsyncSession) -> list[dict[str, Any]]:
        """Build CDEK packages from order items grouped by supplier into a single package."""
        items: list[OrderItem] = list(order.items)
        if not items:
            raise HTTPException(status_code=400, detail="Order has no items")

        total_weight = 0
        package_items = []

        for oi in items:
            product_result = await db.execute(select(Product).where(Product.id == oi.product_id))
            product = product_result.scalars().first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {oi.product_id} not found")

            weight = product.weight_grams or CdekService.DEFAULT_WEIGHT_GRAMS
            item_weight = weight * oi.quantity
            total_weight += item_weight

            package_items.append({
                "name": product.name[:255],
                "ware_key": (product.sku or str(product.id))[:20],
                "payment": {"value": 0},
                "cost": float(product.price),
                "weight": weight,
                "amount": oi.quantity,
            })

        # Use dimensions of the first product as a rough estimate or defaults
        first_product = None
        if items:
            first_result = await db.execute(select(Product).where(Product.id == items[0].product_id))
            first_product = first_result.scalars().first()

        length = first_product.length_cm if first_product and first_product.length_cm else CdekService.DEFAULT_DIMENSION_CM
        width = first_product.width_cm if first_product and first_product.width_cm else CdekService.DEFAULT_DIMENSION_CM
        height = first_product.height_cm if first_product and first_product.height_cm else CdekService.DEFAULT_DIMENSION_CM

        return [{
            "number": f"pkg-{order.id}",
            "weight": max(total_weight, 1),
            "length": length,
            "width": width,
            "height": height,
            "items": package_items,
        }]

    @staticmethod
    async def _build_sender(order: Order, db: AsyncSession) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Return (sender_contact, from_location) based on supplier."""
        items: list[OrderItem] = list(order.items)
        if not items:
            return None, None

        product_result = await db.execute(select(Product).where(Product.id == items[0].product_id))
        product = product_result.scalars().first()
        if not product:
            return None, None

        supplier_result = await db.execute(select(Supplier).where(Supplier.id == product.supplier_id))
        supplier = supplier_result.scalars().first()
        if not supplier:
            return None, None

        sender = {
            "name": supplier.sender_name or supplier.name or "Продавец",
            "phones": [{"number": CdekService._phone(supplier.sender_phone)}],
        }

        from_location = None
        if supplier.cdek_shipment_point:
            shipment_point = supplier.cdek_shipment_point
            if shipment_point.isdigit():
                from_location = {"code": int(shipment_point)}
            else:
                city_code = await CdekService.resolve_shipment_city_code(supplier.id, db)
                if city_code is not None:
                    from_location = {"code": city_code}
                else:
                    from_location = {"code": shipment_point}
        elif order.cdek_from_location:
            from_location = order.cdek_from_location

        return sender, from_location

    @staticmethod
    def _build_recipient(order: Order) -> dict[str, Any]:
        name = " ".join(filter(None, [order.recipient_first_name, order.recipient_last_name]))
        if not name:
            name = order.user.full_name if order.user else (order.guest_name or "Получатель")
        phone = order.user.phone if order.user and order.user.phone else order.guest_phone
        return {
            "name": name or "Получатель",
            "phones": [{"number": CdekService._phone(phone)}],
        }

    @staticmethod
    def build_calculate_payload(
        items: list[dict[str, Any]],
        from_location: dict[str, Any],
        to_location: dict[str, Any] | None,
        delivery_point: str | None,
    ) -> dict[str, Any]:
        """Build payload for CDEK calculator."""
        packages = []
        for item in items:
            weight = item.get("weight_grams") or CdekService.DEFAULT_WEIGHT_GRAMS
            qty = item.get("quantity", 1)
            length = item.get("length_cm") or CdekService.DEFAULT_DIMENSION_CM
            width = item.get("width_cm") or CdekService.DEFAULT_DIMENSION_CM
            height = item.get("height_cm") or CdekService.DEFAULT_DIMENSION_CM
            packages.append({
                "weight": weight * qty,
                "length": length,
                "width": width,
                "height": height,
            })

        payload: dict[str, Any] = {
            "type": 1,
            "from_location": from_location,
            "packages": packages,
        }

        if delivery_point:
            payload["delivery_point"] = delivery_point
        elif to_location:
            payload["to_location"] = to_location
        else:
            raise HTTPException(status_code=400, detail="Either delivery_point or to_location is required")

        return payload

    @staticmethod
    async def resolve_shipment_city_code(supplier_id: int, db: AsyncSession) -> int | None:
        """Resolve supplier's CDEK shipment city code from PVZ code, with Redis cache."""
        supplier_result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
        supplier = supplier_result.scalars().first()
        if not supplier or not supplier.cdek_shipment_point:
            return None

        pvz_code = supplier.cdek_shipment_point
        cache_key = f"cdek:pvz:city:{pvz_code}"
        cached = await RedisClient.get(cache_key)
        if cached is not None:
            try:
                return int(cached)
            except (TypeError, ValueError):
                pass

        client = CdekClient()
        try:
            point = await client.get_delivery_point(pvz_code)
        finally:
            await client.close()

        if not point:
            return None

        city_code = point.get("location", {}).get("city_code")
        if city_code is not None:
            await RedisClient.set(cache_key, str(city_code), ttl=PVZ_CITY_CACHE_TTL)
            return int(city_code)
        return None

    @staticmethod
    async def get_cached_pvz(city_code: int, type: str = "PVZ") -> list[dict[str, Any]]:
        """Get delivery points for a city from cache or CDEK API."""
        type = type if type in PVZ_TYPE_WHITELIST else "PVZ"
        cache_key = f"cdek:pvz:city:{city_code}:{type}"
        cached = await RedisClient.get(cache_key)
        if cached is not None:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass

        client = CdekClient()
        try:
            points = await client.get_delivery_points(params={"city_code": city_code, "type": type})
        finally:
            await client.close()

        await RedisClient.set(cache_key, json.dumps(points), ttl=PVZ_LIST_CACHE_TTL)
        return points

    @staticmethod
    def _is_sender_location_error(exc: CdekAPIError) -> bool:
        """Detect CDEK calculator rejection of sender PVZ code."""
        body = exc.response_body or {}
        errors = body.get("errors") if isinstance(body, dict) else None
        if not isinstance(errors, list):
            return False
        return any(
            isinstance(err, dict) and err.get("code") == "v2_sender_location_not_recognized"
            for err in errors
        )

    @staticmethod
    async def calculate_delivery(
        db: AsyncSession,
        items: list[dict[str, Any]],
        supplier_id: int,
        to_location: dict[str, Any] | None,
        delivery_point: str | None,
    ) -> list[dict[str, Any]]:
        """Calculate available CDEK tariffs for cart items."""
        supplier_result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
        supplier = supplier_result.scalars().first()
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        shipment_point = supplier.cdek_shipment_point
        if not shipment_point:
            raise HTTPException(status_code=400, detail="Supplier shipment point is not configured")

        city_code = await CdekService.resolve_shipment_city_code(supplier_id, db)
        from_location: dict[str, Any]
        if city_code is not None:
            from_location = {"code": city_code}
        elif shipment_point.isdigit():
            from_location = {"code": int(shipment_point)}
        else:
            from_location = {"code": shipment_point}

        payload = CdekService.build_calculate_payload(items, from_location, to_location, delivery_point)

        client = CdekClient()
        try:
            result = await client.calculate_tariffs(payload)
        except CdekAPIError as exc:
            # Defensive fallback: if CDEK still rejects the location, retry once
            # with the resolved city_code (in case the initial resolve failed or
            # the numeric shipment_point was treated as a city code).
            if CdekService._is_sender_location_error(exc) and city_code is not None:
                logger.info(
                    "CDEK rejected sender location, retrying with city_code %s",
                    city_code,
                )
                from_location = {"code": city_code}
                payload = CdekService.build_calculate_payload(items, from_location, to_location, delivery_point)
                result = await client.calculate_tariffs(payload)
            else:
                raise
        finally:
            await client.close()

        tariffs = result.get("tariff_codes", [])
        return [
            {
                "tariff_code": t["tariff_code"],
                "tariff_name": t.get("tariff_name", ""),
                "tariff_description": t.get("tariff_description", ""),
                "delivery_mode": t.get("delivery_mode"),
                "price": Decimal(str(t.get("delivery_sum", 0))),
                "period_min": t.get("period_min"),
                "period_max": t.get("period_max"),
                "calendar_min": t.get("calendar_min"),
                "calendar_max": t.get("calendar_max"),
            }
            for t in tariffs
            if t.get("delivery_sum") is not None
        ]

    @staticmethod
    async def create_cdek_order(order: Order, db: AsyncSession) -> dict[str, Any]:
        """Create order in CDEK and return raw API response."""
        if order.cdek_uuid:
            logger.info("Order %s already has CDEK uuid %s, skipping", order.id, order.cdek_uuid)
            return {"entity": {"uuid": order.cdek_uuid}}

        if not order.cdek_tariff_code:
            raise HTTPException(status_code=400, detail="Order has no CDEK tariff code")

        # Reload order with items to avoid lazy load issues in async context
        result = await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items))
        )
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        packages = await CdekService._build_packages(order, db)
        sender, from_location = await CdekService._build_sender(order, db)
        recipient = CdekService._build_recipient(order)

        payload: dict[str, Any] = {
            "type": 1,
            "number": str(order.id),
            "tariff_code": order.cdek_tariff_code,
            "recipient": recipient,
            "packages": packages,
        }

        if sender:
            payload["sender"] = sender

        if from_location:
            payload["from_location"] = from_location

        if order.cdek_delivery_mode == "PVZ" and order.cdek_delivery_point:
            payload["delivery_point"] = order.cdek_delivery_point
        elif order.cdek_to_location:
            payload["to_location"] = order.cdek_to_location
        else:
            raise HTTPException(status_code=400, detail="Order has no delivery address")

        client = CdekClient()
        try:
            result = await client.create_order(payload)
        finally:
            await client.close()

        logger.info("CDEK create order response for order %s: %s", order.id, result)
        return result

    @staticmethod
    async def handle_order_status_webhook(payload: dict[str, Any], db: AsyncSession) -> None:
        """Process CDEK ORDER_STATUS webhook."""
        attributes = payload.get("attributes", {})
        cdek_number = attributes.get("cdek_number")
        im_number = attributes.get("number")
        status_code = attributes.get("code")

        if not cdek_number and not im_number:
            logger.warning("CDEK webhook missing cdek_number and number: %s", payload)
            return

        query = select(Order)
        if im_number and im_number.startswith("order-"):
            order_id = int(im_number.replace("order-", ""))
            query = query.where(Order.id == order_id)
        elif cdek_number:
            query = query.where(Order.cdek_number == cdek_number)
        else:
            logger.warning("Cannot identify order from CDEK webhook: %s", payload)
            return

        result = await db.execute(query)
        order = result.scalars().first()
        if not order:
            logger.warning("Order not found for CDEK webhook: cdek_number=%s im_number=%s", cdek_number, im_number)
            return

        order.cdek_number = cdek_number
        order.cdek_status = status_code
        if cdek_number and not order.tracking_number:
            order.tracking_number = cdek_number

        # Map CDEK statuses to internal order statuses
        shipped_statuses = {
            "ACCEPTED_AT_SHIPMENT_WAREHOUSE",
            "TAKEN_BY_TRANSPORT",
            "ACCEPTED_AT_DELIVERY_WAREHOUSE",
            "OUT_FOR_DELIVERY",
        }
        if status_code in shipped_statuses and order.status in ("pending", "paid"):
            order.status = "shipped"
        elif status_code == "DELIVERED" and order.status != "delivered":
            order.status = "delivered"
        elif status_code in ("NOT_DELIVERED", "RETURNED") and order.status not in ("cancelled", "delivered"):
            order.status = "cancelled"

        await db.commit()
        logger.info("Updated order %s from CDEK webhook status=%s", order.id, status_code)
