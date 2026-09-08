"""Загрузчик intake-файлов 1С из MinIO в PostgreSQL (D-13, Фаза 4 #120).

job_worker забирает job ONEC_INTAKE_PROCESS (payload {"intake_id": ...}) →
process_intake читает raw-файл через StorageService.download_raw → определяет
формат (ZIP с CommerceML 2.x / OData JSON, см. docs/onec/FORMAT_MAP.md) →
upsert в каталог по onec_id (categories → products → attributes → values →
prices → stock) батчами с commit на батч → отчёт в onec_intake_log
(status parsed/failed, счётчики — в processing_log job'а) → enqueue
Job(SEARCH_INDEX_PRODUCTS) на затронутые товары.

Идемпотентность: все вставки — upsert по onec_id / unique(product_id,
attribute_id), повторный разбор того же файла не создаёт новых записей.
Soft-delete: DeletionMark=true / ПометкаУдаления → is_active=false.
"""

import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from itertools import batched
from typing import Any
from uuid import UUID
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.models.attribute import Attribute, AttributeValueType, ProductAttributeValue
from src.app.models.category import Category
from src.app.models.job import Job
from src.app.models.onec_sync import OnecIntakeLog
from src.app.models.product import Product
from src.app.services.onec_units import parse_value_with_unit
from src.app.services.price_service import get_site_price, upsert_product_price
from src.app.services.storage_service import storage

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

# Нулевой GUID 1С = NULL во всех перекрёстных ссылках (FORMAT_MAP.md §5).
NULL_GUID = "00000000-0000-0000-0000-000000000000"

# Классификация ValueType.Types[0] определения характеристики (FORMAT_MAP.md §3).
_VALUE_TYPE_MAP = {
    "CatalogRef.ЗначенияСвойствОбъектов": AttributeValueType.enum,
    "Number": AttributeValueType.number,
    "String": AttributeValueType.string,
    "Boolean": AttributeValueType.bool,
}


def odata_attribute_value_type(type_name: str | None) -> AttributeValueType:
    """ValueType.Types[0] определения характеристики → AttributeValueType.

    Общий хелпер для OData-ветки intake loader'а и pull-синка
    (onec_sync_service): неизвестный/отсутствующий тип → string.
    """
    if type_name is None:
        return AttributeValueType.string
    return _VALUE_TYPE_MAP.get(type_name, AttributeValueType.string)


@dataclass
class LoadStats:
    """Счётчики разбора intake-файла (уходят в processing_log job'а)."""

    categories_created: int = 0
    categories_updated: int = 0
    products_created: int = 0
    products_updated: int = 0
    products_deactivated: int = 0
    attributes_created: int = 0
    attributes_updated: int = 0
    values_upserted: int = 0
    prices_applied: int = 0
    stock_applied: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"categories +{self.categories_created}/~{self.categories_updated}, "
            f"products +{self.products_created}/~{self.products_updated}/"
            f"-{self.products_deactivated}, "
            f"attributes +{self.attributes_created}/~{self.attributes_updated}, "
            f"values {self.values_upserted}, prices {self.prices_applied}, "
            f"stock {self.stock_applied}, skipped {self.skipped}, "
            f"errors {len(self.errors)}"
        )


# ─── Определение формата (по логике scripts/onec_format_analyzer.py) ──────────


def _detect_format(data: bytes) -> str:
    """Сниффинг формата: zip / odata_json / commerceml / json / xml / unknown.

    Смотрим только в первые ~64 КБ документа (F005): полный json.loads на
    этом этапе удваивал бы CPU/память — повторный парс всё равно делает
    _load_odata_doc.
    """
    if data[:4] == b"PK\x03\x04":
        return "zip"
    stripped = data.lstrip()
    if stripped.startswith(b"{"):
        head = stripped[:65536]
        if b'"odata.metadata"' in head or b'"odata.error"' in head:
            return "odata_json"
        return "json"
    if stripped.startswith(b"<"):
        head = data[:65536].decode("utf-8", errors="ignore")
        if "КоммерческаяИнформация" in head:
            return "commerceml"
        return "xml"
    return "unknown"


# Лимит суммарного размера распакованного ZIP (F004, защита от zip-bomb):
# 4× лимита intake-тела (100 МБ сжатых → не более 400 МБ распакованных).
ZIP_MAX_EXTRACTED_BYTES = 400 * 1024 * 1024


def _extract_zip(
    data: bytes, _depth: int = 0, _budget: list[int] | None = None
) -> list[tuple[str, bytes]]:
    """Рекурсивная распаковка ZIP → список (имя, байты).

    _budget — одноэлементный список с суммарным размером уже распакованных
    данных (общий на всю рекурсию); при превышении ZIP_MAX_EXTRACTED_BYTES —
    ValueError (файл уйдёт в failed по штатному пути).
    """
    if _budget is None:
        _budget = [0]
    if _depth > 3:
        return [("nested.zip", data)]
    items: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            payload = zf.read(info.filename)
            _budget[0] += len(payload)
            if _budget[0] > ZIP_MAX_EXTRACTED_BYTES:
                raise ValueError(
                    f"ZIP extracted size exceeds {ZIP_MAX_EXTRACTED_BYTES} bytes "
                    "(possible zip-bomb)"
                )
            if payload[:4] == b"PK\x03\x04":
                items.extend(_extract_zip(payload, _depth + 1, _budget))
            else:
                items.append((info.filename, payload))
    return items


def _odata_entity_name(metadata_url: str) -> str:
    """Имя набора сущностей из odata.metadata (формы $metadata#Entity,
    #Collection(StandardODATA.Entity), #Entity/@Element)."""
    fragment = metadata_url.rsplit("#", 1)[-1] if "#" in metadata_url else metadata_url
    fragment = fragment.split("/")[0]
    if fragment.startswith("Collection(StandardODATA."):
        return fragment[len("Collection(StandardODATA."):-1]
    return fragment


def _cml_role(root: ElementTree.Element) -> str:
    """Роль CommerceML-документа: import (каталог) / offers (предложения)."""
    if root.find(".//ПакетПредложений") is not None:
        return "offers"
    if root.find(".//Каталог") is not None:
        return "import"
    return "commerceml"


# ─── Upsert-примитивы ─────────────────────────────────────────────────────────


def _is_null_guid(value: Any) -> bool:
    return value is None or value == NULL_GUID or value == ""


class _CatalogCache:
    """In-run кэши справочников, чтобы не дёргать БД на каждую запись."""

    def __init__(self) -> None:
        self.categories: dict[str, Category] = {}
        self.products: dict[str, Product] = {}
        self.attributes: dict[str, Attribute] = {}
        # Справочник enum-значений (Catalog_ЗначенияСвойствОбъектов),
        # наполняется, если тот же пакет содержит этот entity-set.
        self.property_values: dict[str, str] = {}
        # Товары, реально изменённые в этом прогоне (F007) — только они идут
        # в payload SEARCH_INDEX_PRODUCTS; идемпотентный reparse не ставит job.
        self.touched: set[Product] = set()
        # onec_id товаров, помеченных удалёнными в этом прогоне (F003): цена
        # не реанимирует такой товар.
        self.deleted: set[str] = set()
        # Индекс sku → onec_id (F008): проверка sku-конфликта за O(1)
        # вместо линейного скана cache.products на каждый товар.
        self.skus: dict[str, str] = {}


def _register_product(cache: _CatalogCache, onec_id: str, product: Product) -> None:
    """Положить товар в кэш и поддержать sku-индекс (F008)."""
    cache.products[onec_id] = product
    if product.sku:
        cache.skus[product.sku] = onec_id


async def _upsert_category(
    session: AsyncSession,
    cache: _CatalogCache,
    stats: LoadStats,
    onec_id: str,
    name: str,
    parent_onec_id: str | None,
    is_active: bool,
) -> None:
    category = cache.categories.get(onec_id)
    if category is None:
        result = await session.execute(select(Category).where(Category.onec_id == onec_id))
        category = result.scalar_one_or_none()
    if category is None:
        # Дедупликация: усваиваем существующую категорию с тем же именем,
        # созданную вручную/seed'ом (onec_id IS NULL — никогда не из 1С),
        # вместо создания дубля. Категории с другим onec_id не трогаем —
        # защита от слияния разных 1С-групп с одинаковыми именами.
        result = await session.execute(
            select(Category)
            .where(Category.name == name, Category.onec_id.is_(None))
            .order_by(Category.id)
            .limit(1)
        )
        category = result.scalars().first()
        if category is not None:
            category.onec_id = onec_id
    if category is None:
        category = Category(onec_id=onec_id, name=name, is_active=is_active)
        session.add(category)
        stats.categories_created += 1
    else:
        category.name = name
        category.is_active = is_active
        stats.categories_updated += 1
    category.onec_sync_at = datetime.now(timezone.utc)
    cache.categories[onec_id] = category
    # parent_id резолвим вторым проходом по кэшу, когда все группы загружены
    if parent_onec_id and not _is_null_guid(parent_onec_id):
        parent = cache.categories.get(parent_onec_id)
        if parent is not None and parent.id is not None:
            category.parent_id = parent.id


async def _upsert_product(
    session: AsyncSession,
    cache: _CatalogCache,
    stats: LoadStats,
    onec_id: str,
    name: str,
    sku: str | None,
    description: str | None,
    category_onec_id: str | None,
    weight_grams: int,
    is_active: bool,
) -> Product | None:
    """Upsert товара по onec_id; None — запись пропущена (правило «активные»).

    F003: новый товар создаётся с is_active=False и без цены — в
    каталоге он появится только после применения первой валидной сайтовой
    цены > 0 (правило «цена > 0», B-01). F002: sku, занятый другим товаром (1С не
    гарантирует уникальность Артикул), не присваивается — warning + errors,
    импорт не падает (poison-файл недопустим). F007: в cache.touched
    попадают только реально изменённые товары.
    """
    product = cache.products.get(onec_id)
    if product is None:
        result = await session.execute(select(Product).where(Product.onec_id == onec_id))
        product = result.scalar_one_or_none()

    created = product is None
    if created:
        if not is_active:
            # Первое появление товара — уже с пометкой удаления: создавать нечего.
            stats.skipped += 1
            return None
        if settings.onec_default_supplier_id is None:
            raise ValueError(
                "ONEC_DEFAULT_SUPPLIER_ID is required to create products from intake"
            )
        product = Product(
            onec_id=onec_id,
            name=name,
            stock=0,
            supplier_id=settings.onec_default_supplier_id,
            # F003: до первой валидной сайтовой цены товар не показывается в каталоге
            is_active=False,
        )
        session.add(product)
        stats.products_created += 1
        cache.touched.add(product)
    else:
        stats.products_updated += 1
        if not is_active and product.is_active:
            stats.products_deactivated += 1

    if not is_active:
        cache.deleted.add(onec_id)

    def _set(attr: str, value: Any) -> None:
        if getattr(product, attr) != value:
            setattr(product, attr, value)
            cache.touched.add(product)

    _set("name", name or product.name)
    if sku:
        # F008: O(1) проверка по in-run индексу; DB-select только при промахе
        holder = cache.skus.get(sku)
        sku_taken = holder is not None and holder != onec_id
        if not sku_taken and holder is None:
            result = await session.execute(
                select(Product.id).where(Product.sku == sku, Product.onec_id != onec_id)
            )
            sku_taken = result.first() is not None
        if sku_taken:
            # F002: дубль Артикула — не присваиваем sku, файл не становится poison
            logger.warning(
                "SKU %r already taken by another product — skipped for onec_id=%r",
                sku,
                onec_id,
            )
            stats.errors.append(f"duplicate sku {sku!r} for {onec_id}")
        else:
            if product.sku and product.sku != sku and cache.skus.get(product.sku) == onec_id:
                # Переназначение sku: старый ключ индекса больше не валиден
                del cache.skus[product.sku]
            _set("sku", sku)
            cache.skus[sku] = onec_id
    if description is not None:
        _set("description", description)
    _set("weight_grams", weight_grams or product.weight_grams or 1000)
    if not created:
        if not is_active:
            _set("is_active", False)
        elif product.is_active or await get_site_price(session, product.id) is not None:
            # «Восстановление» из DeletionMark — только у товара с валидной
            # сайтовой ценой; товар без цены остаётся неактивным (F003), иначе
            # reparse того же файла активировал бы его без offers.
            # get_site_price вызывается лениво (short-circuit): только для
            # неактивного товара, без лишнего запроса на каждый активный.
            _set("is_active", True)
    product.onec_sync_at = datetime.now(timezone.utc)

    if not _is_null_guid(category_onec_id):
        category = cache.categories.get(category_onec_id)
        if category is None:
            result = await session.execute(
                select(Category).where(Category.onec_id == category_onec_id)
            )
            category = result.scalar_one_or_none()
            if category is not None:
                cache.categories[category_onec_id] = category
        _set("category_id", category.id if category else None)

    _register_product(cache, onec_id, product)
    return product


async def _upsert_attribute(
    session: AsyncSession,
    cache: _CatalogCache,
    stats: LoadStats,
    onec_id: str,
    name: str,
    value_type: AttributeValueType,
) -> Attribute:
    """Upsert справочника атрибутов по onec_id (code = onec_id, D-05)."""
    attribute = cache.attributes.get(onec_id)
    if attribute is None:
        result = await session.execute(
            select(Attribute).where(Attribute.onec_id == onec_id)
        )
        attribute = result.scalar_one_or_none()
    if attribute is None:
        attribute = Attribute(
            code=onec_id,
            onec_id=onec_id,
            name=name or onec_id,
            value_type=value_type,
            is_filterable=False,
        )
        session.add(attribute)
        stats.attributes_created += 1
    else:
        attribute.name = name or attribute.name
        attribute.value_type = value_type
        stats.attributes_updated += 1
    cache.attributes[onec_id] = attribute
    return attribute


async def _upsert_attribute_value(
    session: AsyncSession,
    cache: _CatalogCache,
    stats: LoadStats,
    product: Product,
    attribute: Attribute,
    raw_value: Any,
) -> None:
    """Upsert значения характеристики с нормализацией единиц (D-10)."""
    await session.flush()  # гарантируем id у свежих product/attribute

    if isinstance(raw_value, bool):
        number, unit, text, bool_value = None, None, None, raw_value
    else:
        parsed = parse_value_with_unit(None if raw_value is None else str(raw_value))
        number, unit, text, bool_value = parsed.number, parsed.unit, parsed.text, None
        if attribute.value_type == AttributeValueType.bool:
            bool_value = (text or "").strip().lower() in ("true", "да", "1")
            number, text = None, None if bool_value else text
        if unit and attribute.unit is None:
            # Базовая единица атрибута фиксируется по первому числовому значению (D-10)
            attribute.unit = unit

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
        cache.touched.add(product)  # F007: переиндекс нужен только при изменении
    elif (
        value.value_number != number
        or value.value_text != text
        or value.value_bool != bool_value
    ):
        cache.touched.add(product)
    value.value_number = number
    value.value_text = text
    value.value_bool = bool_value
    stats.values_upserted += 1


# ─── OData JSON (FORMAT_MAP.md §§1–5) ─────────────────────────────────────────


async def _load_odata_categories(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, records: list[dict]
) -> None:
    pending_parents: list[tuple[str, str]] = []
    for batch in batched(records, BATCH_SIZE):
        for rec in batch:
            onec_id = rec.get("Ref_Key")
            if not onec_id:
                stats.skipped += 1
                continue
            parent_onec_id = rec.get("Parent_Key")
            await _upsert_category(
                session,
                cache,
                stats,
                onec_id=onec_id,
                name=rec.get("Description") or onec_id,
                parent_onec_id=parent_onec_id,
                is_active=not rec.get("DeletionMark", False),
            )
            if not _is_null_guid(parent_onec_id):
                pending_parents.append((onec_id, parent_onec_id))
        await session.commit()
    # Второй проход parent_id (родитель мог идти позже в файле)
    for onec_id, parent_onec_id in pending_parents:
        category = cache.categories.get(onec_id)
        parent = cache.categories.get(parent_onec_id)
        if category is not None and parent is not None and parent.id is not None:
            category.parent_id = parent.id
    await session.commit()


async def _load_odata_products(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, records: list[dict]
) -> None:
    for batch in batched(records, BATCH_SIZE):
        for rec in batch:
            onec_id = rec.get("Ref_Key")
            if not onec_id:
                stats.skipped += 1
                continue
            # Правило «активные» (FORMAT_MAP.md §5): папки и услуги не загружаем
            if rec.get("IsFolder"):
                stats.skipped += 1
                continue
            type_ = rec.get("ТипНоменклатуры")
            if type_ is not None and type_ != "Запас":
                stats.skipped += 1
                continue
            weight_kg = rec.get("Вес") or 0
            try:
                weight_grams = int(float(weight_kg) * 1000) or 1000
            except (TypeError, ValueError):
                weight_grams = 1000
            await _upsert_product(
                session,
                cache,
                stats,
                onec_id=onec_id,
                name=rec.get("Description") or onec_id,
                sku=rec.get("Артикул") or rec.get("Code"),
                description=rec.get("НаименованиеПолное") or rec.get("Description"),
                category_onec_id=rec.get("КатегорияНоменклатуры_Key"),
                weight_grams=weight_grams,
                is_active=not rec.get("DeletionMark", False),
            )
        await session.commit()


async def _load_odata_attribute_defs(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, records: list[dict]
) -> None:
    for rec in records:
        onec_id = rec.get("Ref_Key")
        if not onec_id:
            stats.skipped += 1
            continue
        types = (rec.get("ValueType") or {}).get("Types") or []
        await _upsert_attribute(
            session,
            cache,
            stats,
            onec_id=onec_id,
            name=rec.get("Description") or onec_id,
            value_type=odata_attribute_value_type(types[0] if types else None),
        )
    await session.commit()


async def _load_odata_property_values(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, records: list[dict]
) -> None:
    """Справочник enum-значений: GUID → Description (in-run кэш).

    Таблица attribute_options не создаётся (out of scope Фазы 4) — кэш живёт
    только на время разбора пакета; enum-значения из других файлов остаются
    GUID-строками (warning в логе).
    """
    for rec in records:
        ref_key = rec.get("Ref_Key")
        description = rec.get("Description")
        if ref_key and description:
            cache.property_values[ref_key] = description
    await session.commit()


async def _load_odata_product_attributes(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, records: list[dict]
) -> None:
    for batch in batched(records, BATCH_SIZE):
        for rec in batch:
            product_onec_id = rec.get("Ref_Key")
            attribute_onec_id = rec.get("Свойство_Key")
            if not product_onec_id or not attribute_onec_id:
                stats.skipped += 1
                continue
            product = cache.products.get(product_onec_id)
            if product is None:
                result = await session.execute(
                    select(Product).where(Product.onec_id == product_onec_id)
                )
                product = result.scalar_one_or_none()
            if product is None:
                stats.skipped += 1
                continue
            _register_product(cache, product_onec_id, product)

            attribute = cache.attributes.get(attribute_onec_id)
            if attribute is None:
                result = await session.execute(
                    select(Attribute).where(Attribute.onec_id == attribute_onec_id)
                )
                attribute = result.scalar_one_or_none()
            if attribute is None:
                # Определение характеристики ещё не загружено — auto-create
                # заглушкой (is_filterable=false), имя подтянется позже (D-05).
                attribute = await _upsert_attribute(
                    session,
                    cache,
                    stats,
                    onec_id=attribute_onec_id,
                    name=attribute_onec_id,
                    value_type=AttributeValueType.string,
                )

            raw_value = rec.get("Значение")
            value_type_name = rec.get("Значение_Type") or ""
            if value_type_name.startswith("CatalogRef.") and isinstance(raw_value, str):
                resolved = cache.property_values.get(raw_value)
                if resolved is None:
                    logger.warning(
                        "Unresolved enum value GUID %r for attribute %r — stored as text",
                        raw_value,
                        attribute_onec_id,
                    )
                    resolved = raw_value
                raw_value = resolved
            elif value_type_name == "Boolean" or isinstance(raw_value, bool):
                raw_value = bool(raw_value)
            elif raw_value is None:
                raw_value = rec.get("ТекстоваяСтрока")

            await _upsert_attribute_value(session, cache, stats, product, attribute, raw_value)
        await session.commit()


async def _load_odata_prices(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, records: list[dict]
) -> None:
    """Пишет ВСЕ актуальные виды цен в product_prices (D-08).

    Фильтрации по одному виду цены больше нет: каждая запись с
    Актуальность=true upsert'ится по (product_id, ВидЦен_Key). Активация
    товара — только при upsert'е сайтового вида (settings.onec_site_price_type).
    """
    for batch in batched(records, BATCH_SIZE):
        for rec in batch:
            if not rec.get("Актуальность", False):
                stats.skipped += 1
                continue
            price_type = rec.get("ВидЦен_Key")
            if _is_null_guid(price_type):
                stats.skipped += 1
                continue
            product_onec_id = rec.get("Номенклатура_Key")
            price = rec.get("Цена")
            if _is_null_guid(product_onec_id) or price is None:
                stats.skipped += 1
                continue
            product = cache.products.get(product_onec_id)
            if product is None:
                result = await session.execute(
                    select(Product).where(Product.onec_id == product_onec_id)
                )
                product = result.scalar_one_or_none()
            if product is None:
                stats.skipped += 1
                continue
            new_price = Decimal(str(price))
            # F003: цена ≤ 0 не перезаписывает валидную (правило «цена > 0», B-01)
            if new_price <= 0:
                logger.warning(
                    "Ignoring non-positive price %r for product %r",
                    price,
                    product_onec_id,
                )
                stats.errors.append(f"non-positive price for {product_onec_id}")
                continue
            # Фиксируем ДО upsert'а: сайтовой строки ещё ни разу не было.
            # Лениво: select только для неактивного товара и сайтового вида.
            was_unpriced = (
                not product.is_active
                and price_type == settings.onec_site_price_type
                and await get_site_price(session, product.id) is None
            )
            _row, changed = await upsert_product_price(
                session,
                product.id,
                price_type,
                new_price,
                sync_at=datetime.now(timezone.utc),
            )
            if changed:
                cache.touched.add(product)  # F007
            # F003/F009: сайтовая цена активирует только товар, который ещё ни
            # разу не был оценён сайтовым видом. Soft-deleted товар с сайтовой
            # ценой ценой НЕ реанимируется: cache.deleted живёт одним
            # прогоном, а файл цен может прийти позже файла с DeletionMark.
            # «Восстановление» такого товара — только товарным документом без
            # DeletionMark (_upsert_product активирует при наличии сайтовой
            # цены). Известный edge: товар, удалённый до первой цены (сайтовой
            # строки всё ещё нет), первой ценой активируется — следующий
            # товарный файл с DeletionMark вернёт is_active=False.
            if (
                not product.is_active
                and product_onec_id not in cache.deleted
                and was_unpriced
            ):
                product.is_active = True
                cache.touched.add(product)
            _register_product(cache, product_onec_id, product)
            stats.prices_applied += 1
        await session.commit()


async def _load_odata_stock(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, records: list[dict]
) -> None:
    totals: dict[str, float] = {}
    for rec in records:
        product_onec_id = rec.get("Номенклатура_Key")
        if _is_null_guid(product_onec_id):
            stats.skipped += 1
            continue
        try:
            totals[product_onec_id] = totals.get(product_onec_id, 0.0) + float(
                rec.get("КоличествоBalance") or 0
            )
        except (TypeError, ValueError):
            stats.skipped += 1
    # F001: итоговый dict тоже батчим — commit на батч, без долгих локов
    for batch in batched(list(totals.items()), BATCH_SIZE):
        for onec_id, total in batch:
            product = cache.products.get(onec_id)
            if product is None:
                result = await session.execute(
                    select(Product).where(Product.onec_id == onec_id)
                )
                product = result.scalar_one_or_none()
            if product is None:
                stats.skipped += 1
                continue
            # Отрицательный остаток клампится в 0 (B-02, FORMAT_MAP.md §5)
            new_stock = max(0, int(total))
            if product.stock != new_stock:
                product.stock = new_stock
                cache.touched.add(product)  # F007
            product.onec_sync_at = datetime.now(timezone.utc)
            _register_product(cache, onec_id, product)
            stats.stock_applied += 1
        await session.commit()


_ODATA_LOADERS = {
    "Catalog_КатегорииНоменклатуры": _load_odata_categories,
    "Catalog_Номенклатура": _load_odata_products,
    "ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения": _load_odata_attribute_defs,
    "Catalog_ЗначенияСвойствОбъектов": _load_odata_property_values,
    "Catalog_Номенклатура_ДополнительныеРеквизиты": _load_odata_product_attributes,
    "InformationRegister_ЦеныНоменклатуры": _load_odata_prices,
    "AccumulationRegister_ЗапасыНаСкладах_Balance": _load_odata_stock,
}


async def _load_odata_doc(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, data: bytes
) -> None:
    try:
        doc = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"Invalid OData JSON payload: {exc}") from exc
    entity_name = _odata_entity_name(doc.get("odata.metadata", ""))
    loader = _ODATA_LOADERS.get(entity_name)
    if loader is None:
        logger.warning("No loader for OData entity %r — skipped", entity_name)
        stats.skipped += len(doc.get("value") or [])
        return
    records = doc.get("value") or []
    await loader(session, cache, stats, records)


# ─── CommerceML 2.x (FORMAT_MAP.md §6, диалект мока Фазы 7) ──────────────────


def _text(parent: ElementTree.Element, tag: str) -> str | None:
    el = parent.find(tag)
    if el is None or el.text is None:
        return None
    return el.text.strip() or None


async def _load_cml_import(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, data: bytes
) -> None:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid CommerceML import XML: {exc}") from exc

    # Классификатор/Группы → categories
    pending_parents: list[tuple[str, str]] = []
    for group in root.findall(".//Классификатор/Группы/Группа"):
        onec_id = _text(group, "Ид")
        if not onec_id:
            stats.skipped += 1
            continue
        parent_onec_id = _text(group, "Родитель")
        await _upsert_category(
            session,
            cache,
            stats,
            onec_id=onec_id,
            name=_text(group, "Наименование") or onec_id,
            parent_onec_id=parent_onec_id,
            is_active=True,
        )
        if parent_onec_id:
            pending_parents.append((onec_id, parent_onec_id))
    await session.commit()
    for onec_id, parent_onec_id in pending_parents:
        category = cache.categories.get(onec_id)
        parent = cache.categories.get(parent_onec_id)
        if category is not None and parent is not None and parent.id is not None:
            category.parent_id = parent.id
    await session.commit()

    # Классификатор/Свойства → attributes
    for prop in root.findall(".//Классификатор/Свойства/Свойство"):
        onec_id = _text(prop, "Ид")
        if not onec_id:
            stats.skipped += 1
            continue
        type_name = _text(prop, "ТипЗначений")
        value_type = (
            AttributeValueType.number if type_name == "Число" else AttributeValueType.string
        )
        await _upsert_attribute(
            session,
            cache,
            stats,
            onec_id=onec_id,
            name=_text(prop, "Наименование") or onec_id,
            value_type=value_type,
        )
    await session.commit()

    # Каталог/Товары/Товар → products + attribute values
    # F001: батчи BATCH_SIZE с commit на батч — без долгих локов на products
    items = root.findall(".//Каталог/Товары/Товар")
    for batch in batched(items, BATCH_SIZE):
        for item in batch:
            onec_id = _text(item, "Ид")
            if not onec_id:
                stats.skipped += 1
                continue
            deleted = (_text(item, "ПометкаУдаления") or "").lower() == "true"
            category_onec_id = None
            groups = item.find("Группы")
            if groups is not None:
                category_onec_id = _text(groups, "Ид")
            product = await _upsert_product(
                session,
                cache,
                stats,
                onec_id=onec_id,
                name=_text(item, "Наименование") or onec_id,
                sku=_text(item, "Артикул"),
                description=_text(item, "Описание"),
                category_onec_id=category_onec_id,
                weight_grams=1000,
                is_active=not deleted,
            )
            if product is None:
                continue
            values_el = item.find("ЗначенияСвойств")
            if values_el is None:
                continue
            for value_el in values_el.findall("ЗначенияСвойства"):
                attribute_onec_id = _text(value_el, "Ид")
                if not attribute_onec_id:
                    continue
                attribute = cache.attributes.get(attribute_onec_id)
                if attribute is None:
                    result = await session.execute(
                        select(Attribute).where(Attribute.onec_id == attribute_onec_id)
                    )
                    attribute = result.scalar_one_or_none()
                if attribute is None:
                    attribute = await _upsert_attribute(
                        session,
                        cache,
                        stats,
                        onec_id=attribute_onec_id,
                        name=attribute_onec_id,
                        value_type=AttributeValueType.string,
                    )
                await _upsert_attribute_value(
                    session, cache, stats, product, attribute, _text(value_el, "Значение")
                )
        await session.commit()


async def _load_cml_offers(
    session: AsyncSession, cache: _CatalogCache, stats: LoadStats, data: bytes
) -> None:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid CommerceML offers XML: {exc}") from exc

    # F001: батчи BATCH_SIZE с commit на батч
    offers = root.findall(".//ПакетПредложений/Предложения/Предложение")
    for batch in batched(offers, BATCH_SIZE):
        for offer in batch:
            onec_id = _text(offer, "Ид")
            if not onec_id:
                stats.skipped += 1
                continue
            product = cache.products.get(onec_id)
            if product is None:
                result = await session.execute(
                    select(Product).where(Product.onec_id == onec_id)
                )
                product = result.scalar_one_or_none()
            if product is None:
                stats.skipped += 1
                continue
            _register_product(cache, onec_id, product)

            # D-08: итерируем ВСЕ Цены/Цена (все виды цен), а не первую.
            for price_node in offer.findall("Цены/Цена"):
                price_el = price_node.find("ЦенаЗаЕдиницу")
                if price_el is None or not price_el.text:
                    continue
                price_type = _text(price_node, "ИдТипаЦены") or settings.onec_site_price_type
                try:
                    new_price = Decimal(price_el.text.strip())
                except ArithmeticError:
                    logger.warning("Bad price %r for product %r", price_el.text, onec_id)
                    stats.errors.append(f"bad price for {onec_id}")
                    continue
                # F003: цена ≤ 0 не перезаписывает валидную (B-01)
                if new_price <= 0:
                    logger.warning(
                        "Ignoring non-positive price %r for product %r",
                        price_el.text,
                        onec_id,
                    )
                    stats.errors.append(f"non-positive price for {onec_id}")
                    continue
                # Лениво: select только для неактивного товара и сайтового вида
                was_unpriced = (
                    not product.is_active
                    and price_type == settings.onec_site_price_type
                    and await get_site_price(session, product.id) is None
                )
                _row, changed = await upsert_product_price(
                    session,
                    product.id,
                    price_type,
                    new_price,
                    sync_at=datetime.now(timezone.utc),
                )
                if changed:
                    cache.touched.add(product)  # F007
                # F003/F009: сайтовая цена активирует только никогда не
                # оценённый сайтовым видом товар; soft-deleted с сайтовой
                # ценой ценой не реанимируется — см. развёрнутый комментарий
                # в _load_odata_prices.
                if (
                    not product.is_active
                    and onec_id not in cache.deleted
                    and was_unpriced
                ):
                    product.is_active = True
                    cache.touched.add(product)
                stats.prices_applied += 1
            qty_el = offer.find("Количество")
            if qty_el is not None and qty_el.text:
                try:
                    # Отрицательный остаток клампится в 0 (B-02)
                    new_stock = max(0, int(float(qty_el.text.strip())))
                except ValueError:
                    logger.warning("Bad quantity %r for product %r", qty_el.text, onec_id)
                    stats.errors.append(f"bad quantity for {onec_id}")
                else:
                    if product.stock != new_stock:
                        product.stock = new_stock
                        cache.touched.add(product)  # F007
                    stats.stock_applied += 1
            product.onec_sync_at = datetime.now(timezone.utc)
        await session.commit()


# ─── Точка входа ──────────────────────────────────────────────────────────────


async def process_intake(session: AsyncSession, intake_id: str) -> LoadStats:
    """Разобрать intake-файл из MinIO и применить к каталогу.

    Возвращает счётчики LoadStats. При ошибке помечает onec_intake_log как
    failed (status + error), коммитит это состояние и пробрасывает исключение
    для retry-механизма job_worker.
    """
    intake_uuid = UUID(intake_id) if isinstance(intake_id, str) else intake_id
    result = await session.execute(
        select(OnecIntakeLog).where(OnecIntakeLog.intake_id == intake_uuid)
    )
    log = result.scalar_one_or_none()
    if log is None:
        raise ValueError(f"OnecIntakeLog {intake_id} not found")

    stats = LoadStats()
    try:
        data = await storage.download_raw(log.object_key, bucket=log.bucket)
        cache = _CatalogCache()

        fmt = _detect_format(data)
        if fmt == "zip":
            docs = _extract_zip(data)
        else:
            docs = [(log.object_key, data)]

        # Порядок применения: справочники и каталог раньше цен/остатков
        role_order = {"commerceml_import": 0, "odata": 0, "commerceml_offers": 1}
        parsed_docs = []
        for name, payload in docs:
            doc_fmt = _detect_format(payload) if fmt == "zip" else fmt
            if doc_fmt == "odata_json":
                parsed_docs.append((role_order["odata"], "odata", name, payload))
            elif doc_fmt == "commerceml":
                try:
                    root = ElementTree.fromstring(payload)
                except ElementTree.ParseError as exc:
                    raise ValueError(f"Invalid XML in {name}: {exc}") from exc
                role = _cml_role(root)
                if role == "import":
                    parsed_docs.append((role_order["commerceml_import"], "cml_import", name, payload))
                elif role == "offers":
                    parsed_docs.append((role_order["commerceml_offers"], "cml_offers", name, payload))
                else:
                    stats.skipped += 1
            else:
                stats.skipped += 1
                logger.warning("Skipping %s: unsupported format %r", name, doc_fmt)
        if not parsed_docs:
            raise ValueError(f"No parseable documents in intake {intake_id} (format {fmt!r})")

        for _order, kind, name, payload in sorted(parsed_docs, key=lambda d: d[0]):
            logger.info("Processing intake %s doc %s as %s", intake_id, name, kind)
            if kind == "odata":
                await _load_odata_doc(session, cache, stats, payload)
            elif kind == "cml_import":
                await _load_cml_import(session, cache, stats, payload)
            else:
                await _load_cml_offers(session, cache, stats, payload)

        # Постановка job SEARCH_INDEX_PRODUCTS на реально изменённые товары
        # (F007: идемпотентный reparse без изменений job не ставит).
        # Handler — ``handle_search_index_products`` в job_worker (Фаза 5, #121).
        touched_ids = [p.id for p in cache.touched if p.id is not None]
        if touched_ids:
            session.add(
                Job(
                    job_type="SEARCH_INDEX_PRODUCTS",
                    payload={"product_ids": sorted(set(touched_ids))},
                )
            )

        log.status = "parsed"
        log.error = None
        await session.commit()
        return stats
    except Exception as exc:
        await session.rollback()
        # Отдельным коммитом фиксируем failed-статус (батч-коммиты выше уже
        # могли частично применить данные — повторный запуск идемпотентен).
        result = await session.execute(
            select(OnecIntakeLog).where(OnecIntakeLog.intake_id == intake_uuid)
        )
        failed_log = result.scalar_one_or_none()
        if failed_log is not None:
            failed_log.status = "failed"
            failed_log.error = str(exc)[:4000]
            await session.commit()
        raise
