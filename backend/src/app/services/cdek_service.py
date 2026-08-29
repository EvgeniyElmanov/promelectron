import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.app.core.constants import PVZ_TYPE_WHITELIST
from src.app.core.redis_client import RedisClient
from src.app.models.cdek_order import CdekOrder, CdekStatusHistory
from src.app.models.order import Order, OrderItem
from src.app.models.product import Product
from src.app.models.supplier import Supplier
from src.app.services.cdek_client import CdekAPIError, CdekClient
from src.app.services.email_service import EmailService
from src.app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

PVZ_CITY_CACHE_TTL = 86400
PVZ_LIST_CACHE_TTL = 21600


class CdekService:
    DEFAULT_WEIGHT_GRAMS = 1000
    DEFAULT_DIMENSION_CM = 10

    # CDEK statuses considered "shipped" for order mapping
    _SHIPPED_CDEK_STATUSES = {
        "ACCEPTED_AT_SHIPMENT_WAREHOUSE",
        "TAKEN_BY_TRANSPORT",
        "ACCEPTED_AT_DELIVERY_WAREHOUSE",
        "OUT_FOR_DELIVERY",
    }

    @staticmethod
    def _phone(phone: str | None) -> str:
        if not phone:
            raise HTTPException(status_code=400, detail="Recipient phone is required")
        cleaned = "".join(c for c in phone if c.isdigit())
        if cleaned.startswith("8") and len(cleaned) == 11:
            cleaned = "7" + cleaned[1:]
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned

    @staticmethod
    def _format_address_string(cdek_order: CdekOrder) -> str:
        if cdek_order.delivery_point:
            return f"ПВЗ {cdek_order.delivery_point}"
        if cdek_order.to_location:
            return cdek_order.to_location.get("address", "")
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
                "cost": float(oi.price_at_time),
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
        cdek_order = order.cdek_order
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
        elif cdek_order and cdek_order.from_location:
            from_location = cdek_order.from_location

        return sender, from_location

    @staticmethod
    def _build_recipient(order: Order) -> dict[str, Any]:
        if order.recipient:
            name = " ".join(
                filter(None, [
                    order.recipient.last_name,
                    order.recipient.first_name,
                    order.recipient.patronymic,
                ])
            )
            phone = order.recipient.phone
        else:
            name = " ".join(filter(None, [order.recipient_first_name, order.recipient_last_name]))
            if not name:
                name = order.user.full_name if order.user else "Получатель"
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
    async def create_cdek_order(order: Order, db: AsyncSession) -> CdekOrder:
        """Create order in CDEK and persist the result on the CdekOrder record.

        If the order already has a CDEK uuid, the existing CdekOrder is returned.
        """
        if order.cdek_order_id is None:
            raise HTTPException(status_code=400, detail="Order has no CDEK delivery record")

        # Reload with items, cdek_order and user to avoid lazy load issues
        result = await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(
                selectinload(Order.items),
                selectinload(Order.cdek_order),
                selectinload(Order.user),
                selectinload(Order.recipient),
            )
        )
        order = result.scalars().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        cdek_order = order.cdek_order
        if cdek_order is None:
            raise HTTPException(status_code=400, detail="Order has no CDEK delivery record")

        if cdek_order.cdek_uuid:
            logger.info("Order %s already has CDEK uuid %s, skipping", order.id, cdek_order.cdek_uuid)
            return cdek_order

        if not cdek_order.tariff_code:
            raise HTTPException(status_code=400, detail="Order has no CDEK tariff code")

        packages = await CdekService._build_packages(order, db)
        sender, from_location = await CdekService._build_sender(order, db)
        recipient = CdekService._build_recipient(order)

        payload: dict[str, Any] = {
            "type": 1,
            # Номер заказа ИМ должен быть уникален среди активных заказов аккаунта CDEK;
            # после reseed БД голый order.id коллидирует со старыми заказами на стенде.
            "number": f"PM-{order.id}-{uuid.uuid4().hex[:6]}",
            "tariff_code": cdek_order.tariff_code,
            "recipient": recipient,
            "packages": packages,
        }

        if sender:
            payload["sender"] = sender

        if from_location:
            payload["from_location"] = from_location

        if cdek_order.delivery_mode == "PVZ" and cdek_order.delivery_point:
            payload["delivery_point"] = cdek_order.delivery_point
        elif cdek_order.to_location:
            payload["to_location"] = cdek_order.to_location
        else:
            raise HTTPException(status_code=400, detail="Order has no delivery address")

        client = CdekClient()
        try:
            result = await client.create_order(payload)
        finally:
            await client.close()

        entity = result.get("entity", {}) if isinstance(result, dict) else {}
        cdek_uuid = entity.get("uuid") if isinstance(entity, dict) else None
        requests = result.get("requests", []) if isinstance(result, dict) else []
        request_state = requests[0].get("state") if isinstance(requests, list) and requests else None

        logger.info(
            "CDEK create order response for order %s: cdek_uuid=%s request_state=%s",
            order.id,
            cdek_uuid,
            request_state,
        )

        if cdek_uuid:
            cdek_order.cdek_uuid = cdek_uuid
            cdek_order.sync_failed = False
            cdek_order.sync_attempts = 0
        else:
            cdek_order.sync_attempts += 1
            cdek_order.sync_failed = True

        await db.commit()
        await db.refresh(cdek_order)
        return cdek_order

    @staticmethod
    def build_tracking_url(cdek_order: CdekOrder | None) -> str | None:
        """Build public CDEK tracking URL.

        Fallback chain: cdek_number -> tracking_number -> cdek_uuid.
        """
        if cdek_order is None:
            return None
        identifier = cdek_order.cdek_number or cdek_order.tracking_number or cdek_order.cdek_uuid
        if not identifier:
            return None
        return f"https://www.cdek.ru/ru/tracking?order_id={identifier}"

    @staticmethod
    def _map_cdek_status_to_order(status_code: str | None) -> str | None:
        if not status_code:
            return None
        if status_code in CdekService._SHIPPED_CDEK_STATUSES:
            return "shipped"
        if status_code == "DELIVERED":
            return "delivered"
        if status_code in ("NOT_DELIVERED", "RETURNED", "CANCELLED"):
            return "cancelled"
        return None

    @staticmethod
    async def apply_cdek_status(
        cdek_order: CdekOrder,
        payload: dict[str, Any],
        db: AsyncSession,
        source: str = "webhook",
    ) -> bool:
        """Apply a CDEK status payload to a CdekOrder and its Order.

        Writes status history idempotently and maps the CDEK status to
        Order.status. Returns True if the CdekOrder was changed.
        """
        # Lock CdekOrder and related Order to prevent race conditions between
        # webhook and polling (D-13).
        result = await db.execute(
            select(CdekOrder)
            .where(CdekOrder.id == cdek_order.id)
            .options(selectinload(CdekOrder.order))
            .with_for_update()
        )
        cdek_order = result.scalars().one()

        order: Order | None = None
        if cdek_order.order_id is not None:
            order_result = await db.execute(
                select(Order)
                .where(Order.id == cdek_order.order_id)
                .options(selectinload(Order.user))
                .with_for_update()
            )
            order = order_result.scalars().one()

        entity = payload.get("entity", payload) if isinstance(payload, dict) else {}
        statuses = entity.get("statuses", []) if isinstance(entity, dict) else []

        # Prefer statuses list, fallback to status_code / code at entity level
        latest_status: dict[str, Any] = {}
        status_code: str | None = None
        status_date_time: datetime | None = None
        city_name: str | None = None

        if isinstance(statuses, list) and statuses:
            latest_status = statuses[0]
        elif isinstance(entity, dict):
            latest_status = {
                "code": entity.get("status_code") or entity.get("code"),
                "date_time": entity.get("status_date_time") or entity.get("date_time"),
                "city_name": entity.get("city_name"),
            }

        if isinstance(latest_status, dict):
            status_code = latest_status.get("code")
            raw_dt = latest_status.get("date_time") or latest_status.get("status_date_time")
            status_date_time = CdekService._parse_status_datetime(raw_dt)
            city_name = latest_status.get("city_name")

        cdek_number = entity.get("cdek_number") if isinstance(entity, dict) else None

        changed = False
        if cdek_number and cdek_order.cdek_number != cdek_number:
            cdek_order.cdek_number = cdek_number
            changed = True

        if cdek_number and not cdek_order.tracking_number:
            cdek_order.tracking_number = cdek_number
            changed = True

        # Проброс трек-номера в заказ. Раньше order.tracking_number заполнялся
        # только при ship; если CDEK присвоил cdek_number позже, поле заказа
        # оставалось пустым. Источник истины — CDEK: ручное значение не перетираем.
        if order and cdek_number and not order.tracking_number:
            order.tracking_number = cdek_number
            changed = True

        if status_code and cdek_order.cdek_status != status_code:
            cdek_order.cdek_status = status_code
            changed = True

        # Upsert status history idempotently
        if status_code and status_date_time:
            history_stmt = pg_insert(CdekStatusHistory).values(
                cdek_order_id=cdek_order.id,
                cdek_status=status_code,
                status_date_time=status_date_time,
                city_name=city_name,
            ).on_conflict_do_nothing(
                index_elements=["cdek_order_id", "cdek_status", "status_date_time"]
            )
            await db.execute(history_stmt)

        # Map to order status
        mapped_status = CdekService._map_cdek_status_to_order(status_code)
        if mapped_status and order:
            if mapped_status == "shipped" and order.status in ("pending", "paid"):
                order.status = "shipped"
                changed = True
            elif mapped_status == "delivered" and order.status != "delivered":
                order.status = "delivered"
                changed = True
            elif mapped_status == "cancelled" and order.status not in ("cancelled", "delivered"):
                order.status = "cancelled"
                changed = True

        if changed:
            await db.commit()
            await db.refresh(cdek_order)

            # Notify customer about automatic status change from CDEK (best-effort)
            if order:
                try:
                    recipient_email = (order.user.email if order.user else None) or order.guest_email
                    if recipient_email:
                        await EmailService.send_order_status_update(
                            to=recipient_email,
                            order_id=order.id,
                            status=order.status,
                            db=db,
                        )

                    if order.user_id:
                        status_labels = {
                            "pending": "Ожидает оплаты",
                            "paid": "Оплачен",
                            "shipped": "Отправлен",
                            "delivered": "Доставлен",
                            "cancelled": "Отменён",
                        }
                        label = status_labels.get(order.status, order.status)
                        await NotificationService.create_notification(
                            db=db,
                            user_id=order.user_id,
                            type="status_changed",
                            title="Статус заказа изменён",
                            message=f"Заказ №{order.id}: {label}",
                            order_id=order.id,
                        )
                except Exception:
                    logger.exception("Failed to send CDEK status notification for order %s", order.id)

            logger.info(
                "Applied CDEK status to cdek_order=%s source=%s status=%s",
                cdek_order.id,
                source,
                status_code,
            )
        else:
            logger.debug(
                "No CDEK status change for cdek_order=%s source=%s status=%s",
                cdek_order.id,
                source,
                status_code,
            )

        return changed

    @staticmethod
    def _parse_status_datetime(raw: Any) -> datetime | None:
        if raw is None:
            return None
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                return raw.replace(tzinfo=timezone.utc)
            return raw
        if isinstance(raw, str):
            # CDEK returns ISO 8601; handle trailing Z
            try:
                normalized = raw.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized)
            except ValueError:
                return None
        return None

    @staticmethod
    async def handle_order_status_webhook(payload: dict[str, Any], db: AsyncSession) -> CdekOrder | None:
        """Process CDEK ORDER_STATUS webhook by normalizing payload and applying status."""
        attributes = payload.get("attributes", {})
        cdek_number = attributes.get("cdek_number")
        im_number = attributes.get("number")
        cdek_uuid = attributes.get("uuid")

        cdek_order: CdekOrder | None = None

        if cdek_uuid:
            result = await db.execute(
                select(CdekOrder)
                .where(CdekOrder.cdek_uuid == cdek_uuid)
                .options(selectinload(CdekOrder.order))
            )
            cdek_order = result.scalars().first()

        if cdek_order is None and cdek_number:
            result = await db.execute(
                select(CdekOrder)
                .where(CdekOrder.cdek_number == cdek_number)
                .options(selectinload(CdekOrder.order))
            )
            cdek_order = result.scalars().first()

        if cdek_order is None and im_number:
            # CDEK may send our internal order id as number
            try:
                order_id = int(im_number)
            except (TypeError, ValueError):
                order_id = None
                if isinstance(im_number, str) and im_number.startswith("PM-"):
                    # Current format "PM-{id}-{suffix}": extract the internal order id
                    parts = im_number.split("-")
                    if len(parts) >= 3:
                        try:
                            order_id = int(parts[1])
                        except ValueError:
                            order_id = None
                elif isinstance(im_number, str) and im_number.startswith("order-"):
                    # Handle "order-{id}" legacy format
                    order_id = int(im_number.replace("order-", ""))

            if order_id is not None:
                result = await db.execute(
                    select(CdekOrder)
                    .where(CdekOrder.order_id == order_id)
                    .options(selectinload(CdekOrder.order))
                )
                cdek_order = result.scalars().first()

        if not cdek_order:
            logger.warning(
                "CdekOrder not found for webhook: cdek_number=%s im_number=%s uuid=%s",
                cdek_number,
                im_number,
                cdek_uuid,
            )
            return None

        # Build entity-shaped payload for apply_cdek_status
        entity_payload = {"entity": attributes}
        await CdekService.apply_cdek_status(cdek_order, entity_payload, db, source="webhook")
        return cdek_order

    @staticmethod
    async def cancel_cdek_order(cdek_uuid: str) -> dict[str, Any]:
        """Cancel (delete) a CDEK order by uuid.

        This is an internal helper for the order-cancellation task. It raises
        CdekAPIError if CDEK refuses the cancellation.
        """
        client = CdekClient()
        try:
            result = await client.delete_order(cdek_uuid)
        finally:
            await client.close()

        entity = result.get("entity", {}) if isinstance(result, dict) else {}
        requests = result.get("requests", []) if isinstance(result, dict) else []
        request_state = requests[0].get("state") if isinstance(requests, list) and requests else None

        logger.info(
            "CDEK cancel order response for uuid=%s: cdek_uuid=%s request_state=%s",
            cdek_uuid,
            entity.get("uuid") if isinstance(entity, dict) else None,
            request_state,
        )
        return result
