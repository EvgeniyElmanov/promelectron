"""Seeder стартового виртуального каталога 1С — электротовары (D-03/D-04).

Детерминированный (rng по catalog_seed). На каждый посеянный товар пишет три
записи change_log (product/price/stock create) в той же транзакции — так
POST /trigger/ после рестарта мока отправляет полный стартовый каталог одним
пакетом (без записей send_pending вернул бы nothing_to_send).

Инвариант формата SKU: `EL-NNNNN` — двухсегментный с числовым хвостом, т.к.
scenarios._scenario_new_products считает следующий SKU как
int(max_sku.split("-")[1]) + 1.
"""

import logging
import random
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onec_mock.config import Settings
from onec_mock.models import (
    Attribute,
    Category,
    ChangeLog,
    Product,
    ProductAttributeValue,
)

logger = logging.getLogger("onec_mock.seed")

ROOT_CATEGORIES = [
    "Электроустановочные изделия",
    "Кабель и провод",
    "Защита и автоматика",
    "Освещение",
    "Щитовое оборудование",
]

CHILD_CATEGORIES = {
    "Электроустановочные изделия": ["Розетки", "Выключатели"],
    "Кабель и провод": ["Кабели силовые", "Провода монтажные"],
    "Защита и автоматика": ["Автоматические выключатели", "УЗО и дифавтоматы"],
    "Освещение": ["Светильники", "Лампы"],
    "Щитовое оборудование": ["Боксы", "DIN-рейка и клеммы"],
}

ATTRIBUTES = [
    ("brand", "Бренд", "text", None),
    ("color", "Цвет", "text", None),
    ("warranty_months", "Гарантия", "number", "мес"),
    ("rated_current_a", "Номинальный ток", "number", "А"),
    ("voltage_v", "Номинальное напряжение", "number", "В"),
    ("wire_cross_section_mm2", "Сечение жилы", "number", "мм²"),
    ("ip_rating", "Степень защиты", "text", None),
    ("mounting_type", "Способ монтажа", "text", None),
]

BRANDS = ["Legrand", "Schneider Electric", "ABB", "IEK", "EKF", "GUSI", "Юпитер"]
COLORS = ["белый", "чёрный", "серый", "слоновая кость"]
INSULATION_COLORS = ["синий", "жёлто-зелёный", "красный", "чёрный"]

RATED_CURRENTS = [6, 10, 16, 20, 25, 32, 40, 63]
VOLTAGES = [220, 250, 380, 400, 660]
WIRE_SECTIONS = [0.5, 0.75, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0]
IP_RATINGS = ["IP20", "IP41", "IP44", "IP54", "IP65"]
MOUNTING_TYPES = ["скрытый", "открытый", "накладной", "на DIN-рейку"]

# Серии по брендам — реалистичные линейки электроустановки и автоматики
SERIES_INSTALL = {
    "Legrand": ["Valena", "Etika"],
    "Schneider Electric": ["AtlasDesign", "Sedna"],
    "ABB": ["Basic55"],
    "IEK": ["FLORIS"],
    "EKF": ["PROxima"],
}
SERIES_PROTECTION = {
    "IEK": ["ВА47-29", "ВА47-60"],
    "ABB": ["S201", "SH201"],
    "Schneider Electric": ["Acti9 iC60N", "Easy9"],
    "EKF": ["PROxima"],
    "Legrand": ["DX3"],
}
SERIES_LIGHTING = {
    "Юпитер": ["Standard"],
    "EKF": ["ДБО"],
    "IEK": ["ДВО"],
    "GUSI": ["Lezard"],
}
SERIES_BOXES = {
    "IEK": ["ЩРН-П"],
    "EKF": ["PROxima"],
    "ABB": ["Mistral65"],
    "Schneider Electric": ["Mini Pragma"],
}

# Шаблоны имён по листовой категории: fmt с плейсхолдерами {brand}/{series}/
# {color}/..., params — словари вариантов (series — по бренду), price — диапазон ₽
PRODUCT_TEMPLATES: dict[str, list[dict]] = {
    "Розетки": [
        {
            "fmt": "Розетка {brand} {series} 2P+E {color}",
            "params": {"series": SERIES_INSTALL},
            "price": (150, 1200),
        },
        {
            "fmt": "Розетка двойная {brand} {series} 2P+E с заземлением {color}",
            "params": {"series": SERIES_INSTALL},
            "price": (300, 1800),
        },
        {
            "fmt": "Розетка компьютерная {brand} {series} RJ45 кат.5e {color}",
            "params": {"series": SERIES_INSTALL},
            "price": (400, 2500),
        },
    ],
    "Выключатели": [
        {
            "fmt": "Выключатель {brand} {series} одноклавишный {color}",
            "params": {"series": SERIES_INSTALL},
            "price": (200, 1500),
        },
        {
            "fmt": "Выключатель {brand} {series} двухклавишный с подсветкой {color}",
            "params": {"series": SERIES_INSTALL},
            "price": (350, 2200),
        },
        {
            "fmt": "Переключатель проходной {brand} {series} {color}",
            "params": {"series": SERIES_INSTALL},
            "price": (500, 2600),
        },
    ],
    "Кабели силовые": [
        {
            "fmt": "Кабель ВВГнг-LS {cores}×{section} ГОСТ 31996-2012",
            "params": {"cores": [2, 3, 5], "section": [1.5, 2.5, 4.0, 6.0, 10.0]},
            "price": (60, 700),
        },
        {
            "fmt": "Кабель NYM {cores}×{section} ГОСТ",
            "params": {"cores": [2, 3], "section": [1.5, 2.5, 4.0, 6.0]},
            "price": (80, 900),
        },
        {
            "fmt": "Кабель ВВГ-Пнг(А)-LS {cores}×{section} плоский",
            "params": {"cores": [2, 3], "section": [1.5, 2.5, 4.0]},
            "price": (55, 650),
        },
    ],
    "Провода монтажные": [
        {
            "fmt": "Провод ПуВ (ПВ-1) 1×{section} {color}",
            "params": {"section": [0.5, 0.75, 1.0, 1.5, 2.5, 4.0], "color": INSULATION_COLORS},
            "price": (50, 300),
        },
        {
            "fmt": "Провод ПВ-3 1×{section} {color}",
            "params": {"section": [1.5, 2.5, 4.0, 6.0], "color": INSULATION_COLORS},
            "price": (50, 350),
        },
        {
            "fmt": "Провод ШВВП {cores}×{section} {color}",
            "params": {"cores": [2, 3], "section": [0.5, 0.75], "color": ["белый", "чёрный"]},
            "price": (50, 200),
        },
    ],
    "Автоматические выключатели": [
        {
            "fmt": "Автомат {brand} {series} {poles}P {current}A {curve}",
            "params": {
                "series": SERIES_PROTECTION,
                "poles": [1, 2, 3],
                "current": RATED_CURRENTS,
                "curve": ["B", "C", "D"],
            },
            "price": (250, 3500),
        },
        {
            "fmt": "Выключатель автоматический {brand} {series} {poles}P {current}A 6кА {curve}",
            "params": {
                "series": SERIES_PROTECTION,
                "poles": [1, 2],
                "current": [6, 10, 16, 20, 25, 32],
                "curve": ["B", "C"],
            },
            "price": (300, 4000),
        },
    ],
    "УЗО и дифавтоматы": [
        {
            "fmt": "УЗО {brand} {series} 2P {current}A 30мА тип AC",
            "params": {
                "series": {
                    "IEK": ["ВД1-63"],
                    "ABB": ["FH202"],
                    "Schneider Electric": ["Acti9 iID"],
                    "EKF": ["PROxima ВД63"],
                },
                "current": [16, 25, 40, 63],
            },
            "price": (1200, 7000),
        },
        {
            "fmt": "Дифавтомат {brand} {series} 2P {current}A C 30мА",
            "params": {
                "series": {
                    "IEK": ["АВДТ-32"],
                    "ABB": ["DS201"],
                    "Schneider Electric": ["Acti9 iDPN"],
                    "EKF": ["PROxima АВДТ"],
                },
                "current": [10, 16, 25, 32],
            },
            "price": (1800, 9000),
        },
    ],
    "Светильники": [
        {
            "fmt": "Светильник накладной LED {brand} {series} {power}Вт {ip} {color}",
            "params": {
                "series": SERIES_LIGHTING,
                "power": [12, 18, 24, 36],
                "ip": ["IP20", "IP44", "IP54"],
                "color": ["белый", "серый", "чёрный"],
            },
            "price": (500, 8000),
        },
        {
            "fmt": "Светильник точечный встраиваемый {brand} {series} GX53 {color}",
            "params": {"series": SERIES_LIGHTING, "color": ["белый", "хром", "чёрный"]},
            "price": (200, 1500),
        },
        {
            "fmt": "Светильник аварийный {brand} {series} БСА LED {power}Вт",
            "params": {"series": {"Юпитер": ["БСА-LED"], "IEK": ["ССА"], "EKF": ["PROxima"]},
                       "power": [1, 3, 6]},
            "price": (900, 6000),
        },
    ],
    "Лампы": [
        {
            "fmt": "Лампа светодиодная {brand} E27 {power}Вт {temp}K",
            "params": {"power": [7, 9, 12, 15], "temp": [2700, 4000, 6500]},
            "price": (80, 600),
        },
        {
            "fmt": "Лампа светодиодная {brand} GU10 {power}Вт {temp}K",
            "params": {"power": [5, 7], "temp": [3000, 4000, 6500]},
            "price": (90, 700),
        },
        {
            "fmt": "Лампа галогенная {brand} G9 {power}Вт",
            "params": {"power": [28, 40]},
            "price": (60, 400),
        },
    ],
    "Боксы": [
        {
            "fmt": "Бокс {brand} {series} ЩРН-{modules} {ip} навесной",
            "params": {
                "series": SERIES_BOXES,
                "modules": [8, 12, 18, 24, 36],
                "ip": ["IP41", "IP55", "IP65"],
            },
            "price": (400, 6000),
        },
        {
            "fmt": "Бокс {brand} {series} ЩРВ-{modules} {ip} встраиваемый",
            "params": {
                "series": SERIES_BOXES,
                "modules": [12, 18, 24, 36],
                "ip": ["IP41", "IP55"],
            },
            "price": (700, 8000),
        },
        {
            "fmt": "Бокс {brand} {series} ЩМП-{size} {ip} с монтажной панелью",
            "params": {"series": SERIES_BOXES, "size": [1, 2, 3], "ip": ["IP54", "IP65"]},
            "price": (1500, 12000),
        },
    ],
    "DIN-рейка и клеммы": [
        {
            "fmt": "DIN-рейка {brand} 35×7.5 перфорированная {length} м",
            "params": {"length": [1, 2]},
            "price": (50, 300),
        },
        {
            "fmt": "Клемма винтовая {brand} ЗНИ-{section}мм² {color}",
            "params": {"section": [1.5, 2.5, 4.0, 6.0, 10.0],
                       "color": ["серый", "синий", "жёлто-зелёный"]},
            "price": (50, 150),
        },
        {
            "fmt": "Клемма пружинная {brand} {series} {poles}-полюсная",
            "params": {"series": {"IEK": ["СК"], "EKF": ["PROxima"]}, "poles": [2, 3, 5]},
            "price": (50, 250),
        },
    ],
}

# Атрибуты, релевантные каждой листовой категории (brand/color/warranty — всем)
LEAF_ATTRS: dict[str, list[str]] = {
    "Розетки": ["brand", "color", "warranty_months", "rated_current_a", "voltage_v",
                "ip_rating", "mounting_type"],
    "Выключатели": ["brand", "color", "warranty_months", "rated_current_a", "voltage_v",
                    "ip_rating", "mounting_type"],
    "Кабели силовые": ["brand", "warranty_months", "wire_cross_section_mm2", "voltage_v"],
    "Провода монтажные": ["brand", "color", "warranty_months", "wire_cross_section_mm2",
                          "voltage_v"],
    "Автоматические выключатели": ["brand", "warranty_months", "rated_current_a",
                                   "voltage_v", "mounting_type"],
    "УЗО и дифавтоматы": ["brand", "warranty_months", "rated_current_a", "voltage_v",
                          "mounting_type"],
    "Светильники": ["brand", "color", "warranty_months", "voltage_v", "ip_rating",
                    "mounting_type"],
    "Лампы": ["brand", "warranty_months", "voltage_v"],
    "Боксы": ["brand", "warranty_months", "ip_rating", "mounting_type"],
    "DIN-рейка и клеммы": ["brand", "warranty_months", "wire_cross_section_mm2",
                           "mounting_type"],
}


def _render_params(rng: random.Random, entry: dict, brand: str) -> dict:
    """Собрать значения плейсхолдеров шаблона имени (series — по бренду)."""
    params: dict = {"brand": brand}
    for key, choices in entry["params"].items():
        if key == "series":
            params[key] = rng.choice(choices[brand])
        else:
            params[key] = rng.choice(choices)
    if "color" not in params:
        params["color"] = rng.choice(COLORS)
    return params


def _attribute_value(
    rng: random.Random, code: str, params: dict
) -> tuple[str | None, Decimal | None]:
    """Значение атрибута; current/section согласованы с именем товара."""
    if code == "brand":
        return params["brand"], None
    if code == "color":
        return params["color"], None
    if code == "warranty_months":
        return None, Decimal(rng.randint(6, 60))
    if code == "rated_current_a":
        return None, Decimal(params.get("current") or rng.choice(RATED_CURRENTS))
    if code == "voltage_v":
        return None, Decimal(rng.choice(VOLTAGES))
    if code == "wire_cross_section_mm2":
        section = params.get("section")
        if section is None:
            section = rng.choice(WIRE_SECTIONS)
        return None, Decimal(str(section))
    if code == "ip_rating":
        return params.get("ip") or rng.choice(IP_RATINGS), None
    if code == "mounting_type":
        return rng.choice(MOUNTING_TYPES), None
    raise ValueError(f"unknown attribute code: {code}")


async def seed_catalog(session: AsyncSession, settings: Settings) -> int:
    """Заполнить каталог стартовым набором, если он пуст. Возвращает число товаров."""
    existing = await session.scalar(select(func.count(Product.id)))
    if existing:
        logger.info("catalog already seeded (%s products), skipping", existing)
        return 0

    rng = random.Random(settings.catalog_seed)

    attributes: list[Attribute] = []
    for code, name, value_type, unit in ATTRIBUTES:
        attr = Attribute(code=code, name=name, value_type=value_type, unit=unit)
        session.add(attr)
        attributes.append(attr)
    await session.flush()

    leaf_categories: list[Category] = []
    for root_name in ROOT_CATEGORIES:
        root = Category(onec_id=str(uuid.UUID(int=rng.getrandbits(128))), name=root_name)
        session.add(root)
        await session.flush()
        for child_name in CHILD_CATEGORIES[root_name]:
            child = Category(
                onec_id=str(uuid.UUID(int=rng.getrandbits(128))),
                name=child_name,
                parent_onec_id=root.onec_id,
            )
            session.add(child)
            leaf_categories.append(child)
    await session.flush()

    for i in range(settings.seed_products_count):
        # round-robin по листовым категориям: каждая категория гарантированно
        # непуста при count >= числа листовых (нужно для фасетов), детерминизм ок
        category = leaf_categories[i % len(leaf_categories)]
        entry = rng.choice(PRODUCT_TEMPLATES[category.name])
        series_map = entry["params"].get("series")
        brand = rng.choice(sorted(series_map)) if series_map else rng.choice(BRANDS)
        params = _render_params(rng, entry, brand)
        name = entry["fmt"].format(**params)
        price = round(rng.uniform(*entry["price"]), 2)
        product = Product(
            onec_id=str(uuid.UUID(int=rng.getrandbits(128))),
            sku=f"EL-{i + 1:05d}",
            name=name,
            description=f"{name}. Категория: {category.name}.",
            category_onec_id=category.onec_id,
            price=price,
            stock=rng.randint(0, 200),
        )
        session.add(product)
        await session.flush()
        for attr in attributes:
            if attr.code not in LEAF_ATTRS[category.name]:
                continue
            value_text, value_number = _attribute_value(rng, attr.code, params)
            session.add(
                ProductAttributeValue(
                    product_id=product.id,
                    attribute_id=attr.id,
                    value_text=value_text,
                    value_number=value_number,
                )
            )
        # План обмена: формат payload 1-в-1 как в scenarios._log (D-03)
        session.add(
            ChangeLog(entity_type="product", entity_onec_id=product.onec_id,
                      action="create", payload={"name": name, "sku": product.sku})
        )
        session.add(
            ChangeLog(entity_type="price", entity_onec_id=product.onec_id,
                      action="create", payload={"new": str(price)})
        )
        session.add(
            ChangeLog(entity_type="stock", entity_onec_id=product.onec_id,
                      action="create", payload={"new": product.stock})
        )

    await session.commit()
    logger.info("catalog seeded: %s products", settings.seed_products_count)
    return settings.seed_products_count
