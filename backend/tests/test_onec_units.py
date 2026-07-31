"""Тесты парсера единиц измерения onec_units (D-10, Фаза 4 #120).

Примеры — из реальных сэмплов Фазы 3 (docs/onec/reports/2026-07-30_march-samples.md)
и карты маппинга docs/onec/FORMAT_MAP.md §3.
"""

from decimal import Decimal

import pytest

from src.app.services.onec_units import parse_value_with_unit


@pytest.mark.parametrize(
    ("raw", "number", "unit"),
    [
        # Числовые кандидаты из сэмплов (FORMAT_MAP.md §3)
        ("10,0мм2", Decimal("10.0"), "мм²"),
        ("16,0мм2", Decimal("16.0"), "мм²"),
        ("1шт", Decimal("1"), "шт"),
        ("2шт", Decimal("2"), "шт"),
        # Запятая как разделитель, без единицы
        ("2,5", Decimal("2.5"), None),
        ("2.5", Decimal("2.5"), None),
        # Пробелы и точка-разделитель с единицей
        (" 2.5 мм² ", Decimal("2.5"), "мм²"),
        # Другие известные единицы нормализуются
        ("3м2", Decimal("3"), "м²"),
        ("1,5мм3", Decimal("1.5"), "мм³"),
        # Целые и отрицательные числа
        ("42", Decimal("42"), None),
        ("-5", Decimal("-5"), None),
    ],
)
def test_parse_numeric_values(raw, number, unit):
    parsed = parse_value_with_unit(raw)
    assert parsed.number == number
    assert parsed.unit == unit
    assert parsed.text is None


@pytest.mark.parametrize(
    "raw",
    [
        # Диапазон — целиком в текст (не range-фасет на этом этапе)
        "1,5-2,5",
        "1.5 - 2.5 мм2",
        "10–16",
        # Значения без буквенной единицы кандидатами не считаются (FORMAT_MAP.md §3)
        "2016/2025/2032",
        # Нечисловые значения
        "чёрный",
        "Без канифоли",
        "IP20",
        "да",
    ],
)
def test_parse_falls_back_to_text(raw):
    parsed = parse_value_with_unit(raw)
    assert parsed.number is None
    assert parsed.unit is None
    assert parsed.text == raw.strip()


def test_parse_none_and_empty():
    assert parse_value_with_unit(None).text is None
    parsed = parse_value_with_unit("")
    assert parsed.number is None
    assert parsed.text == ""


def test_parse_unparsable_logs_warning(caplog):
    with caplog.at_level("WARNING", logger="src.app.services.onec_units"):
        parse_value_with_unit("совсем не число")
    assert "Could not parse attribute value" in caplog.text


def test_parse_range_does_not_log_warning(caplog):
    """Диапазон — осознанный текстовый кейс, warning не нужен."""
    with caplog.at_level("WARNING", logger="src.app.services.onec_units"):
        parse_value_with_unit("1,5-2,5")
    assert caplog.text == ""
