"""OData-контракт поверх схемы onec: реестр сущностей, $filter/$top/$skip, envelope.

Формат ответов сверен с реальными сэмплами 1С:УНФ (см. task.md issue #227).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

NULL_GUID = "00000000-0000-0000-0000-000000000000"

PRODUCT_ATTRIBUTES_VALUE_TYPE = "StandardODATA.Catalog_ЗначенияСвойствОбъектов"


def _guid(value: str) -> str:
    """Пустая строка в данных → нулевой GUID (как реальная 1С)."""
    return value if value else NULL_GUID


def _ts(value: datetime | None) -> str:
    """1С отдаёт даты без таймзоны: 2021-01-03T00:00:00."""
    return value.strftime("%Y-%m-%dT%H:%M:%S") if value else "0001-01-01T00:00:00"


def _num(value: Decimal | None) -> float:
    return float(value) if value is not None else 0.0


def _serialize_attribute_definition(row: dict[str, Any]) -> dict[str, Any]:
    # raw = полный OData record, если заполнен; в дампе raw = NULL — собираем из плоских колонок
    if row["raw"] is not None:
        return row["raw"]
    return {
        "Ref_Key": row["ref_key"],
        "DeletionMark": row["deletion_mark"],
        "Description": row["description"],
        "Заголовок": row["description"],
        "ValueType": {"Types": ["CatalogRef.ЗначенияСвойствОбъектов"]},
    }


@dataclass(frozen=True)
class EntityDef:
    table: str
    columns: list[str]  # select-лист
    serializer: Callable[[dict[str, Any]], dict[str, Any]]
    # OData-имя поля → колонка таблицы (для $filter)
    filter_fields: dict[str, str]


def _serialize_category(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Ref_Key": row["ref_key"],
        "Description": row["description"],
        "Parent_Key": NULL_GUID,
        "IsFolder": False,
        "DeletionMark": row["deletion_mark"],
    }


def _serialize_product(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Ref_Key": row["ref_key"],
        "Description": row["description"],
        "НаименованиеПолное": row["full_name"],
        "Артикул": row["article"],
        "Code": row["code"],
        "Parent_Key": _guid(row["parent_key"]),
        "IsFolder": row["is_folder"],
        "ТипНоменклатуры": row["product_type"],
        "КатегорияНоменклатуры_Key": _guid(row["category_key"]),
        "ЕдиницаИзмерения_Key": _guid(row["unit_key"]),
        "Вес": 0,
        "DeletionMark": row["deletion_mark"],
    }


def _serialize_price(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Period": _ts(row["period"]),
        "ВидЦен_Key": _guid(row["price_type_key"]),
        "Номенклатура_Key": _guid(row["product_key"]),
        "Характеристика_Key": _guid(row["characteristic_key"]),
        "Цена": _num(row["price"]),
        "Актуальность": bool(row["is_actual"]),
    }


def _serialize_stock(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Организация_Key": _guid(row["organization_key"]),
        "Номенклатура_Key": _guid(row["product_key"]),
        "Характеристика_Key": NULL_GUID,
        "Партия_Key": NULL_GUID,
        "СтруктурнаяЕдиница_Key": _guid(row["warehouse_key"]),
        "Ячейка_Key": NULL_GUID,
        "КоличествоBalance": _num(row["quantity"]),
        "КоличествоИнтBalance": 0,
    }


def _serialize_attribute_value(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Ref_Key": row["ref_key"],
        "Description": row["description"],
        "Owner_Key": _guid(row["owner_key"]),
        "DeletionMark": row["deletion_mark"],
    }


def _serialize_product_attribute(row: dict[str, Any]) -> dict[str, Any]:
    value_key = row["value_key"]
    return {
        "Ref_Key": row["product_key"],
        "LineNumber": str(row["line_number"]),
        "Свойство_Key": row["attribute_key"],
        "Значение": _guid(value_key),
        "ТекстоваяСтрока": row["text_value"],
        "Значение_Type": PRODUCT_ATTRIBUTES_VALUE_TYPE if value_key else "Edm.String",
    }


def _serialize_unit(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Ref_Key": row["ref_key"],
        "Description": row["description"],
        "Code": row["code"],
    }


def _serialize_price_type(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Ref_Key": row["ref_key"],
        "Description": row["description"],
        "DeletionMark": row["deletion_mark"],
    }


def _serialize_product_file(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Ref_Key": row["ref_key"],
        "Description": row["description"],
        "ВладелецФайла_Key": row["product_key"],
        "Размер": str(row["file_size"]),
        "Расширение": row["extension"],
        "DeletionMark": row["deletion_mark"],
        "ДатаСоздания": _ts(row["synced_at"]),
    }


ENTITIES: dict[str, EntityDef] = {
    "Catalog_КатегорииНоменклатуры": EntityDef(
        table="categories",
        columns=["ref_key", "description", "deletion_mark"],
        serializer=_serialize_category,
        filter_fields={"Ref_Key": "ref_key", "DeletionMark": "deletion_mark"},
    ),
    "Catalog_Номенклатура": EntityDef(
        table="products",
        columns=[
            "ref_key",
            "parent_key",
            "is_folder",
            "description",
            "full_name",
            "code",
            "article",
            "product_type",
            "category_key",
            "unit_key",
            "deletion_mark",
        ],
        serializer=_serialize_product,
        filter_fields={
            "Ref_Key": "ref_key",
            "ТипНоменклатуры": "product_type",
            "IsFolder": "is_folder",
            "DeletionMark": "deletion_mark",
            "КатегорияНоменклатуры_Key": "category_key",
        },
    ),
    "InformationRegister_ЦеныНоменклатуры": EntityDef(
        table="prices",
        columns=["period", "price_type_key", "product_key", "characteristic_key", "price", "is_actual"],
        serializer=_serialize_price,
        filter_fields={
            "ВидЦен_Key": "price_type_key",
            "Номенклатура_Key": "product_key",
            "Актуальность": "is_actual",
        },
    ),
    "AccumulationRegister_ЗапасыНаСкладах/Balance": EntityDef(
        table="stock_balance",
        columns=["organization_key", "product_key", "warehouse_key", "quantity"],
        serializer=_serialize_stock,
        filter_fields={
            "СтруктурнаяЕдиница_Key": "warehouse_key",
            "Номенклатура_Key": "product_key",
        },
    ),
    "ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения": EntityDef(
        table="attribute_definitions",
        columns=["ref_key", "description", "deletion_mark", "raw"],
        serializer=_serialize_attribute_definition,
        filter_fields={"Ref_Key": "ref_key"},
    ),
    "Catalog_ЗначенияСвойствОбъектов": EntityDef(
        table="attribute_values",
        columns=["ref_key", "description", "owner_key", "deletion_mark"],
        serializer=_serialize_attribute_value,
        filter_fields={"Owner_Key": "owner_key", "Ref_Key": "ref_key"},
    ),
    "Catalog_Номенклатура_ДополнительныеРеквизиты": EntityDef(
        table="product_attributes",
        columns=["product_key", "line_number", "attribute_key", "value_key", "text_value"],
        serializer=_serialize_product_attribute,
        filter_fields={"Ref_Key": "product_key"},
    ),
    "Catalog_КлассификаторЕдиницИзмерения": EntityDef(
        table="units",
        columns=["ref_key", "description", "code"],
        serializer=_serialize_unit,
        filter_fields={"Ref_Key": "ref_key"},
    ),
    "Catalog_ВидыЦен": EntityDef(
        table="price_types",
        columns=["ref_key", "description", "deletion_mark"],
        serializer=_serialize_price_type,
        filter_fields={"Ref_Key": "ref_key"},
    ),
    "Catalog_НоменклатураПрисоединенныеФайлы": EntityDef(
        table="product_files",
        columns=["ref_key", "product_key", "description", "extension", "file_size", "deletion_mark", "synced_at"],
        serializer=_serialize_product_file,
        filter_fields={"ВладелецФайла_Key": "product_key", "Ref_Key": "ref_key"},
    ),
}

# <field> eq 'строка' | <field> eq guid'<guid>' | <field> eq true|false | <field> eq <число>
_FILTER_CLAUSE_RE = re.compile(
    r"^(?P<field>[\wА-Яа-я]+)\s+eq\s+(?:guid'(?P<guid>[^']*)'|'(?P<str>(?:[^']|'')*)'|(?P<atom>\S+))$"
)


class FilterError(ValueError):
    pass


def parse_filter(filter_expr: str, entity: EntityDef) -> tuple[str, dict[str, Any]]:
    """Разобрать поддерживаемое подмножество $filter в WHERE-фрагмент с параметрами."""
    where_parts: list[str] = []
    params: dict[str, Any] = {}
    for i, clause in enumerate(filter_expr.split(" and ")):
        match = _FILTER_CLAUSE_RE.match(clause.strip())
        if not match:
            raise FilterError(f"неподдерживаемое условие $filter: {clause!r}")
        field = match.group("field")
        column = entity.filter_fields.get(field)
        if column is None:
            raise FilterError(f"неподдерживаемое поле $filter: {field!r}")
        param = f"p{i}"
        if match.group("guid") is not None or match.group("str") is not None:
            value: Any = match.group("guid") if match.group("guid") is not None else match.group("str")
            value = value.replace("''", "'")
        else:
            atom = match.group("atom").lower()
            if atom in ("true", "false"):
                value = atom == "true"
            else:
                raise FilterError(f"неподдерживаемый литерал $filter: {match.group('atom')!r}")
        where_parts.append(f"{column} = :{param}")
        params[param] = value
    return " AND ".join(where_parts), params


async def query_entity(
    session: AsyncSession,
    schema: str,
    entity_name: str,
    *,
    filter_expr: str | None,
    top: int,
    skip: int,
) -> list[dict[str, Any]]:
    entity = ENTITIES[entity_name]
    sql = f"SELECT {', '.join(entity.columns)} FROM {schema}.{entity.table}"
    params: dict[str, Any] = {"_top": top, "_skip": skip}
    if filter_expr:
        where, filter_params = parse_filter(filter_expr, entity)
        sql += f" WHERE {where}"
        params.update(filter_params)
    # Детерминированный порядок пагинации: PK id (uuid) есть во всех таблицах onec.*.
    # ORDER BY по неуникальной колонке (ref_key/organization_key) теряет и дублирует
    # строки при постраничном обходе — каждая страница идёт через новое соединение.
    sql += " ORDER BY id LIMIT :_top OFFSET :_skip"
    result = await session.execute(text(sql), params)
    return [entity.serializer(dict(row)) for row in result.mappings()]
