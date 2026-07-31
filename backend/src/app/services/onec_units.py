"""Нормализация значений характеристик 1С на импорте (D-10, Фаза 4 #120).

Строки вида «10,0мм2» парсятся в число + нормализованную единицу
(«мм²»), чтобы заполнить typed-колонки ProductAttributeValue
(value_number + Attribute.unit). Диапазоны («1,5-2,5») и нечисловые
значения остаются текстом (фасет-строка, не range) и логируются.

Таблица KNOWN_UNITS продублирована из scripts/onec_format_analyzer.py
(источник истины по сэмплам Фазы 3): скрипт загружается через importlib
и не может импортировать src.app, поэтому таблица живёт в двух местах —
при изменении синхронизировать обе копии.
"""

import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# Нормализация написания единиц из 1С → каноническая форма (см. FORMAT_MAP.md §3).
KNOWN_UNITS = {
    "мм2": "мм²",
    "м2": "м²",
    "см2": "см²",
    "мм3": "мм³",
    "м3": "м³",
    "": "",
}

_NUMERIC_VALUE_RE = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*([a-zA-Zа-яА-ЯёЁ0-9²³/%]*)\s*$"
)

# Диапазон «1,5-2,5» (дефис/тире между двумя числами, опционально с единицей).
_RANGE_RE = re.compile(
    r"^\s*[+-]?\d+(?:[.,]\d+)?\s*[-–—]\s*[+-]?\d+(?:[.,]\d+)?"
    r"\s*[a-zA-Zа-яА-ЯёЁ0-9²³/%]*\s*$"
)


@dataclass(frozen=True)
class ParsedValue:
    """Результат разбора строки значения характеристики.

    Ровно один вариант заполнен: либо number (+ опционально unit),
    либо text. text=None означает пустое входное значение.
    """

    number: Decimal | None
    unit: str | None
    text: str | None


def parse_value_with_unit(raw: str | None) -> ParsedValue:
    """Разобрать строку значения из 1С.

    - «10,0мм2» → ParsedValue(number=Decimal("10.0"), unit="мм²")
    - «2,5» → ParsedValue(number=Decimal("2.5"), unit=None)
    - «1,5-2,5» → диапазон, весь текст в text (не range-фасет)
    - нечисловое → text + warning-лог
    - None/пустое → text as-is
    """
    if raw is None:
        return ParsedValue(number=None, unit=None, text=None)

    value = raw.strip()
    if not value:
        return ParsedValue(number=None, unit=None, text=raw)

    if _RANGE_RE.match(value):
        return ParsedValue(number=None, unit=None, text=value)

    match = _NUMERIC_VALUE_RE.match(value)
    if match:
        raw_unit = match.group(2)
        # «Единица» без букв («/2025/2032» в «2016/2025/2032») — не единица,
        # а часть нечисловой строки (FORMAT_MAP.md §3: такие значения
        # кандидатами в числовые не считаются).
        unit_has_letters = bool(re.search(r"[a-zA-Zа-яА-ЯёЁ²³%]", raw_unit))
        if not raw_unit or unit_has_letters:
            try:
                number = Decimal(match.group(1).replace(",", "."))
            except InvalidOperation:
                number = None
            if number is not None:
                unit = KNOWN_UNITS.get(raw_unit, raw_unit) or None
                return ParsedValue(number=number, unit=unit, text=None)

    logger.warning("Could not parse attribute value as number+unit: %r", raw)
    return ParsedValue(number=None, unit=None, text=value)
