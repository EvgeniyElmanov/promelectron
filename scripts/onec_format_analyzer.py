#!/usr/bin/env python3
"""Анализатор форматов выгрузок 1С (OData JSON / CommerceML XML / ZIP).

Offline-утилита Фазы 3 эпика #117 (issue #119). Читает локальные файлы
(`--path`) или объекты MinIO (`--minio`, бакет onec-intake), определяет
формат по содержимому, раскладывает записи по реестру сущностей, строит
статистику полей, анализ характеристик и перекрёстные ссылки по GUID,
пишет отчёты markdown + JSON в `docs/onec/reports/`.

Жёсткое правило: скрипт НЕ обращается к продовой 1С (1c.74bita.ru) —
только локальные файлы и MinIO. Приложение (backend/src) не импортируется;
единственная внешняя зависимость — aiobotocore (ленивый импорт, только
в режиме --minio).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

# ─── Константы ───────────────────────────────────────────────────────────────

NULL_GUID = "00000000-0000-0000-0000-000000000000"

GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# «10,0мм2» → (10.0, "мм2"); «1шт» → (1.0, "шт")
NUMERIC_VALUE_RE = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*([a-zA-Zа-яА-ЯёЁ0-9²³/%]*)\s*$"
)

# Нормализация единиц из значений характеристик
KNOWN_UNITS = {
    "мм2": "мм²",
    "м2": "м²",
    "см2": "см²",
    "мм3": "мм³",
    "м3": "м³",
    "": "",
}

# Реестр сущностей OData: имя набора → (ключ, заголовок)
ENTITY_REGISTRY = {
    "Catalog_Номенклатура": ("products", "Номенклатура (товары)"),
    "Catalog_КатегорииНоменклатуры": ("categories", "Категории номенклатуры"),
    "ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения": (
        "attribute_defs",
        "Определения доп. реквизитов и сведений",
    ),
    "Catalog_Номенклатура_ДополнительныеРеквизиты": (
        "product_attributes",
        "Значения доп. реквизитов номенклатуры",
    ),
    "Catalog_ЗначенияСвойствОбъектов": ("property_values", "Значения свойств объектов"),
    "InformationRegister_ЦеныНоменклатуры": ("prices", "Цены номенклатуры"),
    "AccumulationRegister_ЗапасыНаСкладах_Balance": ("stock", "Остатки на складах (Balance)"),
    "Catalog_КлассификаторЕдиницИзмерения": ("units", "Классификатор единиц измерения"),
    "Catalog_ВидыЦен": ("price_types", "Виды цен"),
}

DISTINCT_CAP = 1000  # ограничение на множество distinct-значений
EXAMPLES_CAP = 3

# ─── Источники данных ────────────────────────────────────────────────────────


def iter_local_files(path: str, glob_pattern: str = "*", limit: int | None = None):
    """Итератор (имя, байты) по локальному файлу или каталогу."""
    p = Path(path)
    if p.is_file():
        yield p.name, p.read_bytes()
        return
    if not p.is_dir():
        raise FileNotFoundError(f"Путь не найден: {path}")
    count = 0
    for child in sorted(p.glob(glob_pattern)):
        if not child.is_file():
            continue
        yield child.name, child.read_bytes()
        count += 1
        if limit is not None and count >= limit:
            return


async def _iter_minio_objects_async(
    bucket: str,
    prefix: str,
    endpoint: str,
    access_key: str,
    secret_key: str,
    secure: bool,
    limit: int | None = None,
):
    """Итератор (key, байты) по объектам MinIO/S3. Ленивый импорт aiobotocore."""
    from aiobotocore.session import get_session  # noqa: PLC0415

    scheme = "https" if secure else "http"
    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=f"{scheme}://{endpoint}",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    ) as client:
        count = 0
        continuation: str | None = None
        while True:
            kwargs: dict = {"Bucket": bucket, "Prefix": prefix}
            if continuation:
                kwargs["ContinuationToken"] = continuation
            page = await client.list_objects_v2(**kwargs)
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                body = await (await client.get_object(Bucket=bucket, Key=key))["Body"].read()
                yield key, body
                count += 1
                if limit is not None and count >= limit:
                    return
            if not page.get("IsTruncated"):
                return
            continuation = page.get("NextContinuationToken")


def iter_minio_objects(**kwargs):
    """Синхронная обёртка над асинхронным итератором MinIO."""

    async def _collect():
        return [item async for item in _iter_minio_objects_async(**kwargs)]

    return asyncio.run(_collect())


# ─── Классификация формата и сущностей ───────────────────────────────────────


def detect_format(name: str, data: bytes) -> str:
    """Сниффинг формата по содержимому: zip / odata_json / commerceml / xml / unknown."""
    if data[:4] == b"PK\x03\x04":
        return "zip"
    stripped = data.lstrip()
    if stripped.startswith(b"{"):
        try:
            doc = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            return "unknown"
        if "odata.metadata" in doc or "odata.error" in doc:
            return "odata_json"
        return "json"
    if stripped.startswith(b"<"):
        head = data[:65536].decode("utf-8", errors="ignore")
        if "КоммерческаяИнформация" in head:
            return "commerceml"
        return "xml"
    return "unknown"


def extract_zip(name: str, data: bytes, _depth: int = 0):
    """Рекурсивно распаковывает ZIP, возвращает список (имя, байты)."""
    if _depth > 3:
        return [(name, data)]
    items = []
    with zipfile.ZipFile(BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            payload = zf.read(info.filename)
            if payload[:4] == b"PK\x03\x04":
                items.extend(extract_zip(f"{name}!{info.filename}", payload, _depth + 1))
            else:
                items.append((f"{name}!{info.filename}", payload))
    return items


def classify_odata_entity(metadata_url: str) -> str:
    """Извлекает имя набора сущностей из odata.metadata.

    Поддерживает формы:
      ...$metadata#Catalog_Номенклатура
      ...$metadata#Collection(StandardODATA.AccumulationRegister_ЗапасыНаСкладах_Balance)
      ...$metadata#Catalog_НоменклатураПрисоединенныеФайлы/@Element
    """
    fragment = metadata_url.rsplit("#", 1)[-1] if "#" in metadata_url else metadata_url
    fragment = fragment.split("/")[0]
    m = re.match(r"Collection\(StandardODATA\.(.+)\)", fragment)
    if m:
        return m.group(1)
    return fragment


def classify_cml_role(root: ElementTree.Element) -> str:
    """Роль CommerceML-документа: import (каталог) / offers (предложения)."""
    if root.find(".//ПакетПредложений") is not None:
        return "offers"
    if root.find(".//Каталог") is not None:
        return "import"
    return "commerceml"


def entity_bucket(entity_name: str) -> str:
    """Ключ секции отчёта для сущности; неизвестные — «прочие»."""
    if entity_name in ENTITY_REGISTRY:
        return ENTITY_REGISTRY[entity_name][0]
    return "other"


# ─── Анализ записей ──────────────────────────────────────────────────────────


def _json_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def is_active_record(bucket: str, record: dict) -> bool:
    """Правило «активные» (D-09)."""
    if record.get("DeletionMark", False):
        return False
    if bucket == "products":
        return record.get("ТипНоменклатуры") == "Запас" and not record.get("IsFolder", False)
    if bucket == "prices":
        return bool(record.get("Актуальность", False))
    return True


def analyze_records(records: list[dict], bucket: str) -> dict:
    """Статистика полей: типы, fill rate, distinct, примеры; счётчики активности."""
    total = len(records)
    active = sum(1 for r in records if is_active_record(bucket, r))
    fields: dict[str, dict] = {}
    for record in records:
        for key, value in record.items():
            entry = fields.setdefault(
                key,
                {"count": 0, "types": Counter(), "distinct": set(), "overflow": False, "examples": []},
            )
            if value is None or value == "":
                continue
            entry["count"] += 1
            entry["types"][_json_type(value)] += 1
            if not entry["overflow"]:
                try:
                    entry["distinct"].add(json.dumps(value, ensure_ascii=False, sort_keys=True))
                except TypeError:
                    entry["distinct"].add(str(type(value)))
                if len(entry["distinct"]) > DISTINCT_CAP:
                    entry["distinct"] = set()
                    entry["overflow"] = True
            if len(entry["examples"]) < EXAMPLES_CAP:
                entry["examples"].append(value)
    out_fields = {}
    for key in sorted(fields):
        entry = fields[key]
        distinct_count: int | str = (
            f">{DISTINCT_CAP}" if entry["overflow"] else len(entry["distinct"])
        )
        examples = []
        for ex in entry["examples"]:
            text = json.dumps(ex, ensure_ascii=False)
            examples.append(text if len(text) <= 80 else text[:77] + "...")
        out_fields[key] = {
            "fill_rate": round(entry["count"] / total, 4) if total else 0.0,
            "types": dict(entry["types"]),
            "distinct": distinct_count,
            "examples": examples,
        }
    return {
        "total": total,
        "active": active,
        "filtered_out": total - active,
        "fields": out_fields,
    }


# ─── Анализ характеристик ────────────────────────────────────────────────────


def parse_numeric_candidate(value: str):
    """«10,0мм2» → (10.0, 'мм²'); не число → None."""
    m = NUMERIC_VALUE_RE.match(value)
    if not m:
        return None
    number = float(m.group(1).replace(",", "."))
    unit = KNOWN_UNITS.get(m.group(2), m.group(2))
    return number, unit


def classify_value_type(value_type: dict | None) -> str:
    """Классификация типа свойства по ValueType.Types[0] (D-04)."""
    types = (value_type or {}).get("Types") or []
    first = types[0] if types else ""
    if "CatalogRef" in first or "EnumRef" in first:
        return "enum"
    if first == "Number":
        return "number"
    if first == "Boolean":
        return "bool"
    if first in ("String", "Date"):
        return "string" if first == "String" else "date"
    return "unknown"


def _numeric_summary(values: Counter) -> tuple[bool, str, list[dict]]:
    """Кандидат в числовые по счётчику значений: (флаг, единица, примеры)."""
    non_empty = {v: c for v, c in values.items() if v}
    numeric = []
    for value, count in non_empty.items():
        parsed = parse_numeric_candidate(value)
        # единица обязательна и должна содержать букву/²³ — иначе это шум
        # («2016/2025/2032» не кандидат в числовые)
        if parsed and parsed[1] and re.search(r"[a-zA-Zа-яА-ЯёЁ²³]", parsed[1]):
            numeric.append((parsed[0], parsed[1], value, count))
    numeric_share = (
        sum(c for *_x, c in numeric) / sum(non_empty.values()) if non_empty else 0.0
    )
    units = Counter(unit for _n, unit, _v, c in numeric for _ in range(c))
    return (
        bool(numeric) and numeric_share >= 0.5,
        units.most_common(1)[0][0] if units else "",
        [{"raw": v, "number": n, "unit": u} for n, u, v, _c in numeric[:EXAMPLES_CAP]],
    )


def analyze_attributes(
    attribute_defs: list[dict],
    product_attributes: list[dict],
    property_values: list[dict],
    top: int = 10,
) -> dict:
    """Джойн определений × значений по GUID в памяти.

    Возвращает справочник характеристик: тип, частотность, заполняемость,
    top-N значений, кандидаты в числовые с единицами. Дополнительно анализирует
    Catalog_ЗначенияСвойствОбъектов по Owner_Key — на обрезанных сэмплах значения
    («10,0мм2») часто есть, а назначений в product_attributes нет.
    """
    defs_by_guid = {d.get("Ref_Key"): d for d in attribute_defs if d.get("Ref_Key")}
    values_by_guid = {v.get("Ref_Key"): v for v in property_values if v.get("Ref_Key")}

    stats: dict[str, dict] = {}
    total_assignments = len(product_attributes)
    for row in product_attributes:
        prop_guid = row.get("Свойство_Key")
        if not prop_guid or prop_guid == NULL_GUID:
            continue
        definition = defs_by_guid.get(prop_guid, {})
        name = definition.get("Description") or prop_guid
        entry = stats.setdefault(
            prop_guid,
            {
                "name": name,
                "value_type": classify_value_type(definition.get("ValueType")),
                "count": 0,
                "values": Counter(),
                "missing_definition": not definition,
                "source": "product_attributes",
            },
        )
        entry["count"] += 1
        raw = row.get("Значение")
        if isinstance(raw, str) and GUID_RE.match(raw) and raw != NULL_GUID:
            value_doc = values_by_guid.get(raw)
            display = value_doc.get("Description") if value_doc else f"<broken:{raw}>"
        elif raw in (None, "", NULL_GUID):
            display = row.get("ТекстоваяСтрока") or ""
        else:
            display = str(raw)
        entry["values"][display] += 1

    # Второй проход: значения свойств по владельцу (Owner_Key = свойство)
    for value_doc in property_values:
        owner = value_doc.get("Owner_Key")
        if not owner or owner == NULL_GUID:
            continue
        if owner in stats and stats[owner]["count"] > 0:
            continue  # уже покрыто назначениями
        definition = defs_by_guid.get(owner, {})
        entry = stats.setdefault(
            owner,
            {
                "name": definition.get("Description") or owner,
                "value_type": classify_value_type(definition.get("ValueType")),
                "count": 0,
                "values": Counter(),
                "missing_definition": not definition,
                "source": "property_values",
            },
        )
        description = value_doc.get("Description")
        if description:
            entry["values"][description] += 1

    attributes = []
    for guid in sorted(stats, key=lambda g: stats[g]["name"]):
        entry = stats[guid]
        values = entry["values"]
        is_candidate, unit, numeric_examples = _numeric_summary(values)
        attributes.append(
            {
                "guid": guid,
                "name": entry["name"],
                "value_type": entry["value_type"],
                "assignments": entry["count"],
                "fill_rate": round(entry["count"] / total_assignments, 4)
                if total_assignments
                else 0.0,
                "distinct": len(values),
                "top_values": [
                    {"value": v, "count": c} for v, c in values.most_common(top)
                ],
                "numeric_candidate": is_candidate,
                "numeric_unit": unit,
                "numeric_examples": numeric_examples,
                "missing_definition": entry["missing_definition"],
                "source": entry["source"],
            }
        )
    return {
        "total_definitions": len(attribute_defs),
        "total_assignments": total_assignments,
        "attributes": attributes,
    }


# ─── Перекрёстные ссылки по GUID ─────────────────────────────────────────────


def cross_reference_report(entities: dict[str, list[dict]]) -> dict:
    """Проверка *_Key ссылок против вселенной Ref_Key; нулевой GUID = NULL (D-08)."""
    universe: set[str] = set()
    for records in entities.values():
        for record in records:
            key = record.get("Ref_Key")
            if isinstance(key, str) and GUID_RE.match(key) and key != NULL_GUID:
                universe.add(key)

    links: dict[str, Counter] = {}
    broken_examples: dict[str, list[str]] = {}
    for bucket, records in entities.items():
        for record in records:
            for field_name, value in record.items():
                if not field_name.endswith("_Key") or field_name == "Ref_Key":
                    continue
                if not isinstance(value, str) or not GUID_RE.match(value):
                    continue
                if value == NULL_GUID:
                    continue  # нулевой GUID = NULL
                link_name = f"{bucket}.{field_name}"
                links.setdefault(link_name, Counter())
                if value in universe:
                    links[link_name]["ok"] += 1
                else:
                    links[link_name]["broken"] += 1
                    examples = broken_examples.setdefault(link_name, [])
                    if len(examples) < EXAMPLES_CAP:
                        examples.append(value)
    return {
        "universe_size": len(universe),
        "links": {
            name: {
                "ok": counts["ok"],
                "broken": counts["broken"],
                "broken_examples": broken_examples.get(name, []),
            }
            for name, counts in sorted(links.items())
        },
    }


# ─── CommerceML ──────────────────────────────────────────────────────────────


def analyze_commerceml(name: str, data: bytes) -> dict:
    """Минимальный анализ CommerceML 2.x: роль, счётчики сущностей, образцы полей."""
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        return {"file": name, "role": "commerceml", "parse_error": str(exc)}
    role = classify_cml_role(root)
    products = root.findall(".//Каталог/Товары/Товар")
    offers = root.findall(".//ПакетПредложений/Предложения/Предложение")
    sample_fields: list[str] = []
    for node in (products or offers)[:1]:
        sample_fields = sorted(child.tag for child in node)
    return {
        "file": name,
        "role": role,
        "products_count": len(products),
        "offers_count": len(offers),
        "sample_fields": sample_fields,
    }


# ─── Сводный анализ ──────────────────────────────────────────────────────────


@dataclass
class AnalysisResult:
    source: str
    files: list[dict] = field(default_factory=list)
    entities: dict[str, list[dict]] = field(default_factory=dict)
    entity_names: dict[str, str] = field(default_factory=dict)  # bucket → имя набора 1С
    commerceml: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def analyze_items(items, source: str) -> AnalysisResult:
    """Полный проход по (имя, байты): формат → сущность → записи."""
    result = AnalysisResult(source=source)
    expanded: list[tuple[str, bytes]] = []
    for name, data in items:
        fmt = detect_format(name, data)
        if fmt == "zip":
            try:
                expanded.extend(extract_zip(name, data))
            except zipfile.BadZipFile:
                result.errors.append({"file": name, "error": "bad zip"})
            continue
        expanded.append((name, data))

    for name, data in expanded:
        fmt = detect_format(name, data)
        file_info: dict = {"file": name, "format": fmt, "size": len(data)}
        if fmt == "odata_json":
            doc = json.loads(data)
            if "odata.error" in doc:
                file_info["entity"] = "odata_error"
                file_info["error"] = doc["odata.error"].get("message", {})
                result.errors.append({"file": name, "error": "odata.error"})
            else:
                metadata = doc.get("odata.metadata", "")
                entity_name = classify_odata_entity(metadata)
                bucket = entity_bucket(entity_name)
                file_info["entity"] = entity_name
                file_info["bucket"] = bucket
                records = doc.get("value")
                if records is None:  # форма @Element — одиночный объект
                    records = [{k: v for k, v in doc.items() if not k.startswith("odata.")}]
                file_info["records"] = len(records)
                result.entities.setdefault(bucket, []).extend(records)
                result.entity_names.setdefault(bucket, entity_name)
        elif fmt == "commerceml":
            cml = analyze_commerceml(name, data)
            file_info["role"] = cml.get("role")
            result.commerceml.append(cml)
        result.files.append(file_info)
    return result


def build_stats(result: AnalysisResult, top: int = 10) -> dict:
    """Агрегаты поверх AnalysisResult: поля, характеристики, ссылки, остатки."""
    stats: dict = {"entities": {}}
    for bucket, records in sorted(result.entities.items()):
        stats["entities"][bucket] = analyze_records(records, bucket)

    stats["attributes"] = analyze_attributes(
        result.entities.get("attribute_defs", []),
        result.entities.get("product_attributes", []),
        result.entities.get("property_values", []),
        top=top,
    )
    stats["cross_references"] = cross_reference_report(result.entities)

    # Остатки: сумма КоличествоBalance по номенклатуре, кламп ≥ 0 (B-02/D-09)
    stock_totals: Counter = Counter()
    negative_rows = 0
    min_row_balance: float = 0
    for row in result.entities.get("stock", []):
        qty = row.get("КоличествоBalance", 0) or 0
        if qty < 0:
            negative_rows += 1
            min_row_balance = min(min_row_balance, qty)
        stock_totals[row.get("Номенклатура_Key", NULL_GUID)] += qty
    stats["stock_summary"] = {
        "rows": len(result.entities.get("stock", [])),
        "negative_rows": negative_rows,
        "min_row_balance": min_row_balance,
        "products": len(stock_totals),
        "negative_after_sum": sum(1 for v in stock_totals.values() if v < 0),
        "clamped_to_zero": sum(1 for v in stock_totals.values() if v < 0),
        "min_balance": min(stock_totals.values(), default=0),
    }
    return stats


# ─── Отчёты ──────────────────────────────────────────────────────────────────


def render_markdown(result: AnalysisResult, stats: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Отчёт анализатора форматов 1С — {date.today().isoformat()}")
    lines.append("")
    lines.append(f"- Источник: `{result.source}`")
    lines.append(f"- Файлов обработано: {len(result.files)}")
    lines.append("")

    lines.append("## Файлы и форматы")
    lines.append("")
    lines.append("| Файл | Формат | Сущность | Записей |")
    lines.append("|------|--------|----------|---------|")
    for info in result.files:
        entity = info.get("entity", info.get("role", "—"))
        records = info.get("records", "—")
        lines.append(f"| `{info['file']}` | {info['format']} | {entity} | {records} |")
    lines.append("")

    if result.errors:
        lines.append("## Ошибки / нераспознанное")
        lines.append("")
        for err in result.errors:
            lines.append(f"- `{err['file']}`: {err['error']}")
        lines.append("")

    lines.append("## Сущности")
    lines.append("")
    for bucket, estats in stats["entities"].items():
        entity_name = result.entity_names.get(bucket, bucket)
        title = ENTITY_REGISTRY.get(entity_name, (bucket, entity_name))[1]
        lines.append(f"### {title} (`{entity_name}`)")
        lines.append("")
        lines.append(
            f"Всего: **{estats['total']}**, активных: **{estats['active']}**, "
            f"отфильтровано: {estats['filtered_out']}"
        )
        lines.append("")
        lines.append("| Поле | Fill rate | Типы | Distinct | Примеры |")
        lines.append("|------|-----------|------|----------|---------|")
        for fname, fstats in estats["fields"].items():
            types = ",".join(sorted(fstats["types"]))
            examples = "; ".join(fstats["examples"]).replace("|", "\\|")
            lines.append(
                f"| `{fname}` | {fstats['fill_rate']:.0%} | {types} | "
                f"{fstats['distinct']} | {examples} |"
            )
        lines.append("")

    attrs = stats["attributes"]
    lines.append("## Характеристики (доп. реквизиты)")
    lines.append("")
    lines.append(
        f"Определений: **{attrs['total_definitions']}**, "
        f"назначений: **{attrs['total_assignments']}**"
    )
    lines.append("")
    for attr in attrs["attributes"]:
        marker = " 🔢" if attr["numeric_candidate"] else ""
        lines.append(
            f"### {attr['name']} — {attr['value_type']}{marker}"
        )
        lines.append("")
        lines.append(
            f"- GUID: `{attr['guid']}`; назначений: {attr['assignments']}; "
            f"distinct: {attr['distinct']}; заполняемость: {attr['fill_rate']:.0%}"
        )
        if attr["numeric_candidate"]:
            examples = ", ".join(
                f"«{e['raw']}» → {e['number']} {e['unit']}" for e in attr["numeric_examples"]
            )
            lines.append(
                f"- 🔢 Кандидат в числовые, единица: **{attr['numeric_unit']}**; "
                f"примеры: {examples}"
            )
        if attr["missing_definition"]:
            lines.append("- ⚠️ Определение свойства не найдено в attribute_defs")
        if attr["top_values"]:
            top_str = ", ".join(
                f"«{v['value']}» ×{v['count']}" for v in attr["top_values"]
            )
            lines.append(f"- Top значений: {top_str}")
        lines.append("")

    xref = stats["cross_references"]
    lines.append("## Перекрёстные ссылки по GUID")
    lines.append("")
    lines.append(f"Вселенная GUID (Ref_Key): **{xref['universe_size']}**")
    lines.append("")
    lines.append("| Ссылка | OK | Битых | Примеры битых |")
    lines.append("|--------|----|-------|----------------|")
    for name, link in xref["links"].items():
        examples = ", ".join(f"`{e}`" for e in link["broken_examples"])
        lines.append(f"| `{name}` | {link['ok']} | {link['broken']} | {examples} |")
    lines.append("")

    stock = stats["stock_summary"]
    if stock["rows"]:
        lines.append("## Остатки (Balance)")
        lines.append("")
        lines.append(
            f"- Строк: {stock['rows']}; номенклатуры: {stock['products']}; "
            f"строк с отрицательным остатком: **{stock['negative_rows']}**"
        )
        if stock["negative_rows"]:
            lines.append(
                f"- Минимальный построчный остаток: **{stock['min_row_balance']}**"
            )
        lines.append(
            f"- Минимальный суммарный остаток: **{stock['min_balance']}** "
            f"(кламп ≥ 0 при загрузке, B-02)"
        )
        lines.append("")

    if result.commerceml:
        lines.append("## CommerceML")
        lines.append("")
        for cml in result.commerceml:
            if "parse_error" in cml:
                lines.append(f"- `{cml['file']}`: ошибка парсинга: {cml['parse_error']}")
            else:
                lines.append(
                    f"- `{cml['file']}`: роль **{cml['role']}**, товаров: "
                    f"{cml['products_count']}, предложений: {cml['offers_count']}"
                )
        lines.append("")

    price_types = result.entities.get("price_types", [])
    if price_types:
        lines.append("## Виды цен")
        lines.append("")
        for pt in price_types:
            mark = " (помечен на удаление)" if pt.get("DeletionMark") else ""
            lines.append(f"- `{pt.get('Ref_Key')}` — {pt.get('Description')}{mark}")
        lines.append("")

    return "\n".join(lines)


def result_to_json(result: AnalysisResult, stats: dict) -> dict:
    return {
        "date": date.today().isoformat(),
        "source": result.source,
        "files": result.files,
        "errors": result.errors,
        "commerceml": result.commerceml,
        "entity_names": result.entity_names,
        "stats": stats,
    }


def write_reports(
    result: AnalysisResult, stats: dict, report_dir: str, label: str
) -> tuple[Path, Path]:
    out_dir = Path(report_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{date.today().isoformat()}_{label}"
    md_path = base.with_suffix(".md")
    json_path = base.with_suffix(".json")
    md_path.write_text(render_markdown(result, stats), encoding="utf-8")
    json_path.write_text(
        json.dumps(result_to_json(result, stats), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return md_path, json_path


# ─── CLI ─────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Анализатор форматов выгрузок 1С (OData JSON / CommerceML / ZIP)."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--path", help="Локальный файл или каталог с выгрузками")
    source.add_argument("--minio", action="store_true", help="Читать объекты из MinIO/S3")
    parser.add_argument("--glob", default="*", help="Glob-маска для --path (по умолчанию *)")
    parser.add_argument("--limit", type=int, default=None, help="Максимум файлов/объектов")
    parser.add_argument(
        "--report-dir", default="docs/onec/reports", help="Каталог для отчётов"
    )
    parser.add_argument("--label", default="run", help="Метка отчёта (имя файла)")
    parser.add_argument("--top", type=int, default=10, help="Top-N значений характеристик")
    parser.add_argument("--bucket", default="onec-intake", help="Бакет MinIO")
    parser.add_argument("--prefix", default="", help="Префикс ключей MinIO")
    parser.add_argument("--endpoint", default=os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    parser.add_argument("--access-key", default=os.getenv("MINIO_ACCESS_KEY", ""))
    parser.add_argument("--secret-key", default=os.getenv("MINIO_SECRET_KEY", ""))
    parser.add_argument(
        "--secure",
        action="store_true",
        default=os.getenv("MINIO_SECURE", "").lower() in ("1", "true", "yes"),
        help="HTTPS для MinIO",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.path:
            items = list(iter_local_files(args.path, args.glob, args.limit))
            source = f"local:{args.path} (glob={args.glob})"
        else:
            if not args.access_key or not args.secret_key:
                print(
                    "Ошибка: для --minio нужны --access-key/--secret-key "
                    "или MINIO_ACCESS_KEY/MINIO_SECRET_KEY",
                    file=sys.stderr,
                )
                return 1
            items = iter_minio_objects(
                bucket=args.bucket,
                prefix=args.prefix,
                endpoint=args.endpoint,
                access_key=args.access_key,
                secret_key=args.secret_key,
                secure=args.secure,
                limit=args.limit,
            )
            source = f"minio://{args.bucket}/{args.prefix}"
    except FileNotFoundError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    if not items:
        print("Ошибка: файлы не найдены", file=sys.stderr)
        return 1

    print(f"Прочитано объектов: {len(items)}", file=sys.stderr)
    result = analyze_items(items, source=source)
    stats = build_stats(result, top=args.top)
    md_path, json_path = write_reports(result, stats, args.report_dir, args.label)
    print(f"Markdown-отчёт: {md_path}", file=sys.stderr)
    print(f"JSON-отчёт: {json_path}", file=sys.stderr)
    unknown = [f for f in result.files if f["format"] in ("unknown", "json")]
    if unknown:
        print(
            "Внимание: нераспознанные файлы: "
            + ", ".join(f["file"] for f in unknown),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
