import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from itertools import batched
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.attribute import Attribute, AttributeValueType, ProductAttributeValue
from src.app.models.category import Category
from src.app.models.job import Job
from src.app.models.onec_sync import OnecChangeLog
from src.app.models.product import Product
from src.app.schemas.onec import (
    OnecAttributeDefinitionOdata,
    OnecCategoryOdata,
    OnecChange,
    OnecPriceOdata,
    OnecProductAttributeOdata,
    OnecProductFileOdata,
    OnecProductOdata,
    OnecStockOdata,
    OnecWebhookPayload,
)
from src.app.services import storage_service
from src.app.services.onec_intake_loader import odata_attribute_value_type
from src.app.services.onec_units import parse_value_with_unit
from src.app.services.price_service import upsert_product_price

if TYPE_CHECKING:
    from src.app.workers.onec_client import OnecClient

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


async def _resolve_category_by_id(session: AsyncSession, category_id: str | int | None) -> int | None:
    """Resolve a category identifier to the internal Category.id.

    If the value is a string we treat it as a 1C external id (onec_id).
    If it is already an int we return it as-is.
    """
    if category_id is None:
        return None
    if isinstance(category_id, int):
        return category_id
    result = await session.execute(
        select(Category).where(Category.onec_id == str(category_id))
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise ValueError(f"Category with onec_id={category_id!r} not found")
    return category.id


async def _resolve_category_parent_id(session: AsyncSession, parent_onec_id: str | int | None) -> int | None:
    """Resolve a parent identifier to the internal Category.id.

    If the value is a string we treat it as a 1C external id (onec_id).
    If it is already an int we return it as-is.
    """
    if parent_onec_id is None:
        return None
    if isinstance(parent_onec_id, int):
        return parent_onec_id
    result = await session.execute(
        select(Category).where(Category.onec_id == str(parent_onec_id))
    )
    parent = result.scalar_one_or_none()
    return parent.id if parent else None


def _is_stale_change(change_version: datetime, existing_sync_at: datetime | None) -> bool:
    """Return True if the incoming change is older or equal to the existing entity."""
    if existing_sync_at is None:
        return False
    return change_version <= existing_sync_at


async def _resolve_unique_sku(
    session: AsyncSession, sku: Any, external_id: str
) -> str | None:
    """Нормализовать sku и проверить занятость другим товаром.

    В 1С уникальность Артикула не гарантирована: у разных Ref_Key бывают
    одинаковые артикулы, в т.ч. с хвостовыми пробелами. Дубль не должен
    валить импорт (F002): товар сохраняется с sku=NULL, оригинальный
    артикул остаётся в name. Проверка — явным SELECT, чтобы не ловить
    IntegrityError внутри per-change savepoint'а.
    """
    if sku is None:
        return None
    sku = str(sku).strip()
    if not sku:
        return None
    result = await session.execute(
        select(Product.id).where(
            Product.sku == sku,
            # onec_id NULL (ручные/seed-товары) тоже считаем чужими: `!=` по NULL
            # отфильтровал бы их из выборки
            (Product.onec_id != external_id) | Product.onec_id.is_(None),
        )
    )
    if result.first() is not None:
        logger.warning(
            "SKU %r already taken by another product — sku set to NULL for onec_id=%r",
            sku,
            external_id,
        )
        return None
    return sku


async def apply_product_change(session: AsyncSession, change: OnecChange) -> Product | None:
    """Apply a single 1C product change: create, update or soft-delete."""
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()

    data = change.data
    is_new_product = product is None
    if is_new_product:
        if change.action == "delete":
            return None
        if "supplier_id" not in data:
            raise ValueError("supplier_id is required for product creation")
        if "name" not in data or not data["name"]:
            raise ValueError("name is required for product creation")
        product = Product(onec_id=change.external_id)
        session.add(product)

    if _is_stale_change(change.version, product.onec_sync_at):
        return product

    # Set required fields first so any autoflush triggered by FK resolution
    # (e.g. category_id lookup) or the sku uniqueness SELECT sees a valid
    # product row.
    if "name" in data:
        product.name = data["name"]
    if "description" in data:
        product.description = data["description"]
    if "stock" in data:
        product.stock = data["stock"]
    if "supplier_id" in data:
        product.supplier_id = data["supplier_id"]
    if "is_active" in data:
        product.is_active = data["is_active"]
    if "weight_grams" in data and data["weight_grams"]:
        product.weight_grams = data["weight_grams"]

    # Sku — после обязательных полей: проверка занятости делает SELECT,
    # который вызывает autoflush нового товара.
    if "sku" in data:
        product.sku = await _resolve_unique_sku(session, data["sku"], change.external_id)

    # Resolve foreign keys after all required fields are present.
    if "category_id" in data:
        product.category_id = await _resolve_category_by_id(session, data["category_id"])

    if change.action == "delete":
        product.is_active = False

    product.onec_sync_at = change.version
    return product


async def apply_category_change(session: AsyncSession, change: OnecChange) -> Category | None:
    """Apply a single 1C category change: create, update or soft-delete."""
    result = await session.execute(
        select(Category).where(Category.onec_id == change.external_id)
    )
    category = result.scalar_one_or_none()

    data = change.data
    if category is None:
        if change.action == "delete":
            return None
        if "name" not in data or not data["name"]:
            raise ValueError("name is required for category creation")
        category = Category(onec_id=change.external_id)
        session.add(category)

    if _is_stale_change(change.version, category.onec_sync_at):
        return category

    if "name" in data:
        category.name = data["name"]
    if "description" in data:
        category.description = data["description"]
    if "parent_id" in data:
        category.parent_id = await _resolve_category_parent_id(session, data["parent_id"])
    if "is_active" in data:
        category.is_active = data["is_active"]

    if change.action == "delete":
        category.is_active = False

    category.onec_sync_at = change.version
    return category


async def apply_price_change(session: AsyncSession, change: OnecChange) -> Product | None:
    """Apply a 1C price change to an existing product.

    If the product does not exist yet (e.g. product batch has not been applied)
    the change is silently skipped so the queue stays idempotent.

    Пишет в product_prices (upsert по product_id + price_type, D-06):
    price_type берётся из change.data["price_type_key"], fallback — сайтовый вид.
    Staleness — per-row (product_prices.onec_sync_at), product.onec_sync_at
    ценовые изменения больше не трогают.
    """
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    if "price" in change.data:
        price_value = change.data["price"]
        # F002: "price": null из внешнего JSON — warning + skip, не роняем батч
        if price_value is None:
            logger.warning(
                "Skipping null price for product onec_id=%s",
                change.external_id,
            )
            return product
        price = Decimal(str(price_value)) if not isinstance(price_value, Decimal) else price_value
        if price <= 0:
            logger.warning(
                "Skipping non-positive price %s for product onec_id=%s (B-01)",
                price,
                change.external_id,
            )
            return product
        price_type = change.data.get("price_type_key") or settings.onec_site_price_type
        await upsert_product_price(
            session, product.id, price_type, price, sync_at=change.version
        )

    return product


async def apply_stock_change(session: AsyncSession, change: OnecChange) -> Product | None:
    """Apply a 1C stock balance change to an existing product.

    If the product does not exist yet (e.g. product batch has not been applied)
    the change is silently skipped so the queue stays idempotent.
    Negative stock values are clamped to 0 per business rule B-02.
    """
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    if _is_stale_change(change.version, product.onec_sync_at):
        return product

    if "stock" in change.data:
        stock_value = round(change.data["stock"])
        product.stock = max(stock_value, 0)

    product.onec_sync_at = change.version
    return product


async def apply_product_attributes_change(
    session: AsyncSession, change: OnecChange
) -> Product | None:
    """Apply характеристики товара из 1С (pull-синк, entity_type=product_attributes).

    change.data["attributes"] — список dict с ключами attribute_key
    (onec_id атрибута) и value (уже разрешённое значение: enum-GUID заменён
    на Description на этапе синка). Типизация значения — по семантике
    onec_intake_loader (parse_value_with_unit, D-10). Неизвестный товар или
    атрибут молча пропускаются (цены/остатки/атрибуты в 1С ссылаются на
    товары вне выгруженного подмножества).
    """
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    for item in change.data.get("attributes") or []:
        attribute_key = item.get("attribute_key")
        if not attribute_key:
            continue
        result = await session.execute(
            select(Attribute).where(Attribute.onec_id == attribute_key)
        )
        attribute = result.scalar_one_or_none()
        if attribute is None:
            # Определение ещё не загружено — auto-create заглушкой
            # (is_filterable=false), имя/тип подтянутся следующим синком (D-05).
            attribute = Attribute(
                code=attribute_key,
                onec_id=attribute_key,
                name=attribute_key,
                value_type=AttributeValueType.string,
                is_filterable=False,
            )
            session.add(attribute)
            await session.flush()

        raw_value = item.get("value")
        if isinstance(raw_value, bool):
            number, unit, text, bool_value = None, None, None, raw_value
        else:
            parsed = parse_value_with_unit(None if raw_value is None else str(raw_value))
            number, unit, text, bool_value = parsed.number, parsed.unit, parsed.text, None
            if attribute.value_type == AttributeValueType.bool:
                bool_value = (text or "").strip().lower() in ("true", "да", "1")
                number, text = None, None if bool_value else text
            if unit and attribute.unit is None:
                # Базовая единица атрибута фиксируется по первому числовому
                # значению (D-10)
                attribute.unit = unit

        await session.flush()  # гарантируем id у свежих product/attribute
        result = await session.execute(
            select(ProductAttributeValue).where(
                ProductAttributeValue.product_id == product.id,
                ProductAttributeValue.attribute_id == attribute.id,
            )
        )
        value = result.scalar_one_or_none()
        if value is None:
            value = ProductAttributeValue(product_id=product.id, attribute_id=attribute.id)
            session.add(value)
        value.value_number = number
        value.value_text = text
        value.value_bool = bool_value

    return product


async def apply_product_images_change(
    session: AsyncSession, change: OnecChange
) -> Product | None:
    """Apply изображения товара из 1С (pull-синк, entity_type=product_images).

    change.data["images"] — список URL (products.images — JSON list строк,
    формат читает frontend getImageUrl: строка "/uploads/<key>" или внешний
    URL). Бинарь уже скачан и загружен в storage на этапе синка; здесь только
    идемпотентный merge URL без дублей, порядок — по Description файла.
    Неизвестный товар молча пропускается.
    """
    result = await session.execute(
        select(Product).where(Product.onec_id == change.external_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        return None

    urls = [u for u in (change.data.get("images") or []) if u]
    if not urls:
        return product
    images = list(product.images or [])
    for url in urls:
        if url not in images:
            images.append(url)
    if images != (product.images or []):
        product.images = images
    return product


async def handle_onec_apply_changes(session: AsyncSession, payload: dict) -> None:
    """Process an ONEC_APPLY_CHANGES job payload and update the catalog."""
    log_id = payload.get("log_id")
    if not log_id:
        raise ValueError("ONEC_APPLY_CHANGES job missing log_id")

    result = await session.execute(
        select(OnecChangeLog).where(OnecChangeLog.id == log_id).with_for_update()
    )
    log = result.scalar_one_or_none()
    if not log:
        raise ValueError(f"OnecChangeLog {log_id} not found")

    log.status = "processing"
    log.processed_at = datetime.now(timezone.utc)
    await session.flush()

    try:
        webhook_payload = OnecWebhookPayload.model_validate(log.payload)
        handler = {
            "product": apply_product_change,
            "category": apply_category_change,
            "price": apply_price_change,
            "stock": apply_stock_change,
            "order_status": apply_order_status_change,
            "product_attributes": apply_product_attributes_change,
            "product_images": apply_product_images_change,
        }.get(webhook_payload.entity_type)

        if not handler:
            raise ValueError(f"Unsupported entity_type: {webhook_payload.entity_type}")

        # Per-change savepoint: один битый change (напр. дубль sku из 1С)
        # не валит весь батч — ошибка фиксируется, батч продолжается.
        failed_changes: list[str] = []
        applied_count = 0
        for change in webhook_payload.changes:
            new_before = set(session.new)
            try:
                async with session.begin_nested():
                    await handler(session, change)
                applied_count += 1
            except Exception as exc:
                # Savepoint откатил БД-изменения, но свежие ORM-объекты
                # остаются в session.new и упали бы повторно на commit.
                for obj in set(session.new) - new_before:
                    session.expunge(obj)
                logger.warning(
                    "Failed to apply %s change for %r: %s",
                    webhook_payload.entity_type,
                    change.external_id,
                    exc,
                )
                failed_changes.append(f"{change.external_id}: {exc}")

        if applied_count > 0 or not webhook_payload.changes:
            log.status = "done"
            log.applied_at = datetime.now(timezone.utc)
            log.error_message = (
                f"{len(failed_changes)} change(s) failed: " + "; ".join(failed_changes)
                if failed_changes
                else None
            )
        else:
            # Ни один change не применился — raise уходит во внешний except,
            # который ставит failed/error/retry_count (retry-семантика сохранена)
            raise ValueError("; ".join(failed_changes))
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        log.retry_count += 1
        raise


async def apply_order_status_change(session: AsyncSession, change: OnecChange) -> None:
    """Placeholder for order status changes from 1C.

    order_status handling is out of scope for Phase 1; log and skip silently
    so the queue stays idempotent and does not fail the whole batch.
    """
    logger.warning("order_status changes are not implemented yet: %s", change.external_id)


# ─── Mapping helpers for pull fallback (OData → OnecChange) ──────────────────


def build_category_change(category: OnecCategoryOdata, version: datetime) -> OnecChange:
    return OnecChange(
        external_id=category.ref_key,
        action="update",
        version=version,
        data={
            "name": category.description,
            "parent_id": category.parent_key,
            "is_active": not category.deletion_mark,
        },
    )


def build_product_change(product: OnecProductOdata, version: datetime, supplier_id: int | None) -> OnecChange:
    return OnecChange(
        external_id=product.ref_key,
        action="update",
        version=version,
        data={
            "name": product.description,
            "description": product.full_name or product.description,
            "sku": product.article or product.code,
            # Категория — по КатегорияНоменклатуры_Key (у реальных товаров
            # Parent_Key нулевой, FORMAT_MAP.md §2)
            "category_id": product.category_key,
            "supplier_id": supplier_id,
            "weight_grams": product.weight_grams,
            "is_active": not product.deletion_mark,
        },
    )


def build_price_change(price: OnecPriceOdata, version: datetime) -> OnecChange:
    return OnecChange(
        external_id=price.product_key,
        action="update",
        version=version,
        data={"price": float(price.price), "price_type_key": price.price_type_key},
    )


def build_stock_change(stock: OnecStockOdata, version: datetime) -> OnecChange:
    return OnecChange(
        external_id=stock.product_key,
        action="update",
        version=version,
        data={"stock": round(stock.quantity)},
    )


def build_onec_webhook_payload(
    entity_type: str,
    changes: list[OnecChange],
    batch_id: UUID,
    sent_at: datetime,
    base_name: str,
) -> OnecWebhookPayload:
    return OnecWebhookPayload(
        batch_id=batch_id,
        sent_at=sent_at,
        base_name=base_name,
        entity_type=entity_type,  # type: ignore[arg-type]
        changes=changes,
    )


def _pull_batch_checksum(entity_type: str, changes: list[OnecChange], version: datetime) -> str:
    """Deterministic checksum for a pull fallback batch to avoid duplicates."""
    payload = "|".join(
        [entity_type, version.isoformat()]
        + sorted(change.external_id for change in changes)
    )
    return sha256(payload.encode()).hexdigest()


async def _enqueue_change_log_batch(
    session: AsyncSession,
    entity_type: str,
    changes: list[OnecChange],
    sent_at: datetime,
    base_name: str,
) -> None:
    """Persist one OnecChangeLog + ONEC_APPLY_CHANGES job for a batch of changes."""
    if not changes:
        return
    payload = build_onec_webhook_payload(
        entity_type=entity_type,
        changes=changes,
        batch_id=uuid4(),
        sent_at=sent_at,
        base_name=base_name,
    )
    log = OnecChangeLog(
        batch_id=payload.batch_id,
        entity_type=entity_type,
        source=base_name,
        payload=payload.model_dump(mode="json"),
        status="pending",
        checksum=_pull_batch_checksum(entity_type, changes, sent_at),
    )
    session.add(log)
    await session.flush()
    await session.refresh(log)
    session.add(Job(job_type="ONEC_APPLY_CHANGES", payload={"log_id": log.id}))


async def create_onec_full_sync_job(session: AsyncSession) -> Job:
    """Create an ONEC_FULL_SYNC job for later processing by the worker."""
    job = Job(job_type="ONEC_FULL_SYNC", payload={})
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job


# ─── Pull-синк характеристик и изображений ────────────────────────────────────

# Content-Type загружаемого бинаря по расширению файла 1С.
_IMAGE_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}


async def _upsert_attribute_definitions(
    session: AsyncSession,
    definitions: list[OnecAttributeDefinitionOdata],
) -> None:
    """Upsert справочника Attribute по onec_id (code = onec_id, D-05).

    Применяется напрямую (без OnecChangeLog): определения не зависят от
    товаров и нужны как справочник до батчей product_attributes.
    """
    cache: dict[str, Attribute] = {}
    for defn in definitions:
        attribute = cache.get(defn.ref_key)
        if attribute is None:
            result = await session.execute(
                select(Attribute).where(Attribute.onec_id == defn.ref_key)
            )
            attribute = result.scalar_one_or_none()
        value_type = odata_attribute_value_type(defn.value_type)
        if attribute is None:
            attribute = Attribute(
                code=defn.ref_key,
                onec_id=defn.ref_key,
                name=defn.name or defn.ref_key,
                value_type=value_type,
                is_filterable=False,
            )
            session.add(attribute)
        else:
            attribute.name = defn.name or attribute.name
            attribute.value_type = value_type
        cache[defn.ref_key] = attribute
    await session.flush()


def _resolve_product_attribute_value(
    attr: OnecProductAttributeOdata,
    enum_values: dict[str, str],
) -> object:
    """Разрешить значение строки ТЧ «Дополнительные реквизиты» в текст/bool.

    Семантика — как в OData-ветке onec_intake_loader: ссылочное значение
    (Значение_Type = StandardODATA.Catalog_ЗначенияСвойствОбъектов /
    CatalogRef.*) резолвится в Description справочника значений; иначе —
    ТекстоваяСтрока. Неразрешённый GUID сохраняется текстом (warning).
    """
    type_name = attr.value_type_name or ""
    is_enum_ref = type_name.startswith("CatalogRef.") or type_name.endswith(
        "Catalog_ЗначенияСвойствОбъектов"
    )
    if is_enum_ref and attr.value_key:
        resolved = enum_values.get(attr.value_key)
        if resolved is None:
            logger.warning(
                "Unresolved enum value GUID %r for attribute %r — stored as text",
                attr.value_key,
                attr.attribute_key,
            )
            resolved = attr.value_key
        return resolved
    if type_name == "Boolean":
        return (attr.text_value or "").strip().lower() in ("true", "да", "1")
    return attr.text_value


def _group_attributes_by_product(
    rows: list[OnecProductAttributeOdata],
    enum_values: dict[str, str],
) -> dict[str, list[dict]]:
    """Сгруппировать строки ТЧ по товару: product_key → [{attribute_key, value}]."""
    grouped: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda r: (r.product_key, int(r.line_number or 0))):
        grouped.setdefault(row.product_key, []).append(
            {
                "attribute_key": row.attribute_key,
                "value": _resolve_product_attribute_value(row, enum_values),
            }
        )
    return grouped


async def _enqueue_product_attribute_batches(
    session: AsyncSession,
    rows: list[OnecProductAttributeOdata],
    enum_values: dict[str, str],
    version: datetime,
    base_name: str,
) -> None:
    grouped = _group_attributes_by_product(rows, enum_values)
    changes = [
        OnecChange(
            external_id=product_key,
            action="update",
            version=version,
            data={"attributes": attributes},
        )
        for product_key, attributes in grouped.items()
    ]
    for chunk in batched(changes, BATCH_SIZE):
        await _enqueue_change_log_batch(
            session, "product_attributes", list(chunk), version, base_name
        )


async def _enqueue_product_image_batches(
    session: AsyncSession,
    client: "OnecClient",
    files: list[OnecProductFileOdata],
    version: datetime,
    base_name: str,
) -> None:
    """Скачать бинари файлов, загрузить в storage, enqueue product_images.

    Ключ объекта детерминирован (``onec/<ref_key>.<ext>``) — повторный синк
    перезаписывает тот же объект, дублей URL не плодится. Файлы с
    DeletionMark пропускаются. Порядок URL — по Description файла.
    """
    grouped: dict[str, list[OnecProductFileOdata]] = {}
    for file in files:
        if file.deletion_mark:
            continue
        grouped.setdefault(file.product_key, []).append(file)

    changes: list[OnecChange] = []
    for product_key, product_files in grouped.items():
        urls: list[str] = []
        for file in sorted(product_files, key=lambda f: f.description):
            try:
                binary = await client.download_file_binary(file.ref_key)
            except Exception as exc:
                logger.warning(
                    "Failed to download 1C file %r for product %r: %s",
                    file.ref_key,
                    product_key,
                    exc,
                )
                continue
            ext = file.extension.lower()
            key = f"onec/{file.ref_key}.{ext}"
            content_type = _IMAGE_CONTENT_TYPES.get(ext, "application/octet-stream")
            url = await storage_service.storage.upload_raw(key, binary, content_type)
            urls.append(url)
        if not urls:
            continue
        changes.append(
            OnecChange(
                external_id=product_key,
                action="update",
                version=version,
                data={"images": urls},
            )
        )
    for chunk in batched(changes, BATCH_SIZE):
        await _enqueue_change_log_batch(
            session, "product_images", list(chunk), version, base_name
        )


async def run_onec_full_sync(
    session: AsyncSession,
    default_supplier_id: int | None = None,
) -> None:
    """Pull catalog data from 1C and enqueue ONEC_APPLY_CHANGES jobs.

    This helper is invoked by ``handle_onec_full_sync`` in the job worker.
    Категории/товары/цены/остатки идут через OnecChangeLog → job'ы;
    определения характеристик применяются напрямую (справочник, не зависит
    от товаров); значения характеристик и изображения — батчами после
    товарных (job'ы обрабатываются FIFO, товары к этому моменту созданы).
    """
    from src.app.workers.onec_client import OnecClient

    supplier_id = default_supplier_id or settings.onec_default_supplier_id

    async with OnecClient() as client:
        if not client.base_url:
            raise ValueError("ONEC_API_URL is not configured")

        base_sent_at = datetime.now(timezone.utc)
        base_name = "1c-unf-full-sync"

        # Use monotonically increasing versions per entity type so that
        # price/stock batches are not rejected as stale after product batches.
        def _version(offset_ms: int) -> datetime:
            return base_sent_at + timedelta(milliseconds=offset_ms)

        categories = await client.get_all_categories()
        for chunk in batched(categories, BATCH_SIZE):
            changes = [build_category_change(c, _version(0)) for c in chunk]
            await _enqueue_change_log_batch(session, "category", changes, _version(0), base_name)

        products = await client.get_all_products()
        for chunk in batched(products, BATCH_SIZE):
            changes = [build_product_change(p, _version(100), supplier_id) for p in chunk]
            await _enqueue_change_log_batch(session, "product", changes, _version(100), base_name)

        # Характеристики: определения → справочник значений → связки с товарами
        attribute_definitions = await client.get_all_attribute_definitions()
        await _upsert_attribute_definitions(session, attribute_definitions)
        attribute_values = await client.get_all_attribute_values()
        enum_values = {v.ref_key: v.description for v in attribute_values}
        product_attributes = await client.get_all_product_attributes()
        await _enqueue_product_attribute_batches(
            session, product_attributes, enum_values, _version(400), base_name
        )

        # Изображения: метаданные → бинарь → storage → URL в products.images
        product_files = await client.get_all_product_files()
        await _enqueue_product_image_batches(
            session, client, product_files, _version(500), base_name
        )

        prices = await client.get_all_prices()
        for chunk in batched(prices, BATCH_SIZE):
            changes = [build_price_change(p, _version(200)) for p in chunk]
            await _enqueue_change_log_batch(session, "price", changes, _version(200), base_name)

        stocks = await client.get_all_stock_balance()
        for chunk in batched(stocks, BATCH_SIZE):
            changes = [build_stock_change(s, _version(300)) for s in chunk]
            await _enqueue_change_log_batch(session, "stock", changes, _version(300), base_name)
