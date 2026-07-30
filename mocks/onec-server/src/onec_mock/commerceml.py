"""Генератор CommerceML 2.x пакетов из pending changes (D-05).

Интерфейс PackageGenerator — точка расширения под реальный диалект 1С
после первой живой выгрузки. Реализация CommerceML2Generator генерирует
валидный CommerceML 2.10: import.xml (Классификатор + Каталог) и
offers.xml (ПакетПредложений), упакованные в ZIP (D-02).
"""

import io
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from onec_mock.models import (
    Attribute,
    Category,
    ChangeLog,
    Product,
    ProductAttributeValue,
)

SCHEMA_VERSION = "2.10"
CLASSIFIER_ID = "1"
CATALOG_ID = "2"
OFFERS_ID = "3"
PRICE_TYPE_ID = "BASE"
CURRENCY = "RUB"


@dataclass
class Package:
    import_xml: str
    offers_xml: str
    zip_bytes: bytes = field(repr=False)


class PackageGenerator(ABC):
    """Интерфейс генератора пакета выгрузки (точка расширения формата, D-05)."""

    @abstractmethod
    async def build(self, session: AsyncSession, changes: list[ChangeLog]) -> Package:
        """Собрать пакет (import.xml + offers.xml + ZIP) из списка изменений."""
        raise NotImplementedError


def _sub(
    parent: ET.Element, tag: str, text: str | None = None, attrib: dict | None = None
) -> ET.Element:
    el = ET.SubElement(parent, tag, attrib or {})
    if text is not None:
        el.text = text
    return el


def _root() -> ET.Element:
    return ET.Element(
        "КоммерческаяИнформация",
        {
            "ВерсияСхемы": SCHEMA_VERSION,
            "ДатаФормирования": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
            "СодержитТолькоИзменения": "true",
        },
    )


class CommerceML2Generator(PackageGenerator):
    """Генератор CommerceML 2.10 (xml.etree.ElementTree, без сторонних библиотек)."""

    async def build(self, session: AsyncSession, changes: list[ChangeLog]) -> Package:
        product_ids = {
            c.entity_onec_id
            for c in changes
            if c.entity_type in ("product", "price", "stock")
        }
        deleted_ids = {
            c.entity_onec_id
            for c in changes
            if c.entity_type == "product" and c.action == "delete"
        }

        products: list[Product] = []
        if product_ids:
            products = list(
                (
                    await session.execute(
                        select(Product).where(Product.onec_id.in_(product_ids))
                    )
                ).scalars()
            )
        products_by_onec_id = {p.onec_id: p for p in products}

        categories: list[Category] = list(
            (await session.execute(select(Category).where(Category.is_active.is_(True)))).scalars()
        )
        attributes: list[Attribute] = list((await session.execute(select(Attribute))).scalars())
        attr_by_id = {a.id: a for a in attributes}

        attr_values: dict[int, list[ProductAttributeValue]] = {}
        if products:
            rows = (
                await session.execute(
                    select(ProductAttributeValue).where(
                        ProductAttributeValue.product_id.in_([p.id for p in products])
                    )
                )
            ).scalars()
            for row in rows:
                attr_values.setdefault(row.product_id, []).append(row)

        import_xml = self._build_import(
            changes, products_by_onec_id, deleted_ids, categories, attributes, attr_values, attr_by_id
        )
        offers_xml = self._build_offers(changes, products_by_onec_id, deleted_ids)
        zip_bytes = self._zip(import_xml, offers_xml)
        return Package(import_xml=import_xml, offers_xml=offers_xml, zip_bytes=zip_bytes)

    def _build_import(
        self,
        changes: list[ChangeLog],
        products_by_onec_id: dict[str, Product],
        deleted_ids: set[str],
        categories: list[Category],
        attributes: list[Attribute],
        attr_values: dict[int, list[ProductAttributeValue]],
        attr_by_id: dict[int, Attribute],
    ) -> str:
        root = _root()

        classifier = _sub(root, "Классификатор")
        _sub(classifier, "Ид", CLASSIFIER_ID)
        _sub(classifier, "Наименование", "Классификатор (Каталог товаров)")
        groups_el = _sub(classifier, "Группы")
        for cat in categories:
            group = _sub(groups_el, "Группа")
            _sub(group, "Ид", cat.onec_id)
            _sub(group, "Наименование", cat.name)
            if cat.parent_onec_id:
                _sub(group, "Родитель", cat.parent_onec_id)
        props_el = _sub(classifier, "Свойства")
        for attr in attributes:
            prop = _sub(props_el, "Свойство")
            _sub(prop, "Ид", attr.onec_id)
            _sub(prop, "Наименование", attr.name)
            _sub(prop, "ТипЗначений", "Число" if attr.value_type == "number" else "Строка")

        catalog = _sub(root, "Каталог", attrib={"СодержитТолькоИзменения": "true"})
        _sub(catalog, "Ид", CATALOG_ID)
        _sub(catalog, "ИдКлассификатора", CLASSIFIER_ID)
        _sub(catalog, "Наименование", "Каталог товаров")
        items_el = _sub(catalog, "Товары")
        seen: set[str] = set()
        for change in changes:
            if change.entity_type not in ("product", "price", "stock"):
                continue
            onec_id = change.entity_onec_id
            if onec_id in seen:
                continue
            seen.add(onec_id)
            product = products_by_onec_id.get(onec_id)
            if onec_id in deleted_ids:
                item = _sub(items_el, "Товар")
                _sub(item, "Ид", onec_id)
                _sub(item, "Наименование", change.payload.get("name", ""))
                _sub(item, "ПометкаУдаления", "true")
                continue
            if product is None:
                continue
            item = _sub(items_el, "Товар")
            _sub(item, "Ид", product.onec_id)
            _sub(item, "Артикул", product.sku)
            _sub(item, "Наименование", product.name)
            groups = _sub(item, "Группы")
            _sub(groups, "Ид", product.category_onec_id)
            if product.description:
                _sub(item, "Описание", product.description)
            values_el = _sub(item, "ЗначенияСвойств")
            for value in attr_values.get(product.id, []):
                attr = attr_by_id.get(value.attribute_id)
                if attr is None:
                    continue
                value_el = _sub(values_el, "ЗначенияСвойства")
                _sub(value_el, "Ид", attr.onec_id)
                _sub(
                    value_el,
                    "Значение",
                    str(value.value_number) if value.value_number is not None else (value.value_text or ""),
                )

        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    def _build_offers(
        self,
        changes: list[ChangeLog],
        products_by_onec_id: dict[str, Product],
        deleted_ids: set[str],
    ) -> str:
        root = _root()
        pack = _sub(root, "ПакетПредложений", attrib={"СодержитТолькоИзменения": "true"})
        _sub(pack, "Ид", OFFERS_ID)
        _sub(pack, "Наименование", "Пакет предложений (Каталог товаров)")
        _sub(pack, "ИдКаталога", CATALOG_ID)
        _sub(pack, "ИдКлассификатора", CLASSIFIER_ID)
        offers_el = _sub(pack, "Предложения")
        seen: set[str] = set()
        for change in changes:
            if change.entity_type not in ("product", "price", "stock"):
                continue
            onec_id = change.entity_onec_id
            if onec_id in deleted_ids or onec_id in seen:
                continue
            product = products_by_onec_id.get(onec_id)
            if product is None:
                continue
            seen.add(onec_id)
            offer = _sub(offers_el, "Предложение")
            _sub(offer, "Ид", product.onec_id)
            _sub(offer, "Артикул", product.sku)
            _sub(offer, "Наименование", product.name)
            prices_el = _sub(offer, "Цены")
            price_el = _sub(prices_el, "Цена")
            _sub(price_el, "Представление", f"{product.price} {CURRENCY} за шт.")
            _sub(price_el, "ИдТипаЦены", PRICE_TYPE_ID)
            _sub(price_el, "ЦенаЗаЕдиницу", str(product.price))
            _sub(price_el, "Валюта", CURRENCY)
            _sub(offer, "Количество", str(product.stock))
        return ET.tostring(root, encoding="unicode", xml_declaration=True)

    @staticmethod
    def _zip(import_xml: str, offers_xml: str) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("import.xml", import_xml)
            archive.writestr("offers.xml", offers_xml)
        return buffer.getvalue()
