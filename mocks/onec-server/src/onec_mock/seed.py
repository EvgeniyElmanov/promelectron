"""Seeder стартового виртуального каталога 1С (детерминированный, D-10)."""

import logging
import random
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from onec_mock.config import Settings
from onec_mock.models import Attribute, Category, Product, ProductAttributeValue

logger = logging.getLogger("onec_mock.seed")

ROOT_CATEGORIES = [
    "Электроника",
    "Комплектующие",
    "Периферия",
    "Сетевое оборудование",
    "Расходные материалы",
]

CHILD_CATEGORIES = {
    "Электроника": ["Ноутбуки", "Смартфоны", "Планшеты"],
    "Комплектующие": ["Процессоры", "Видеокарты", "Оперативная память", "Накопители"],
    "Периферия": ["Клавиатуры", "Мыши", "Мониторы"],
    "Сетевое оборудование": ["Маршрутизаторы", "Коммутаторы"],
    "Расходные материалы": ["Картриджи", "Кабели"],
}

ATTRIBUTES = [
    ("brand", "Бренд", "text", None),
    ("warranty_months", "Гарантия, мес.", "number", "мес"),
    ("weight_kg", "Вес", "number", "кг"),
    ("color", "Цвет", "text", None),
]

BRANDS = ["Acer", "ASUS", "HP", "Lenovo", "Samsung", "Xiaomi", "D-Link", "TP-Link"]
COLORS = ["чёрный", "белый", "серый", "синий"]


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
        category = rng.choice(leaf_categories)
        product = Product(
            onec_id=str(uuid.UUID(int=rng.getrandbits(128))),
            sku=f"SKU-{i + 1:05d}",
            name=f"{category.name} товар {i + 1}",
            description=f"Тестовый товар {i + 1} категории {category.name}",
            category_onec_id=category.onec_id,
            price=round(rng.uniform(500, 150000), 2),
            stock=rng.randint(0, 200),
        )
        session.add(product)
        await session.flush()
        for attr in attributes:
            if attr.value_type == "number":
                value_number = (
                    rng.randint(6, 36) if attr.code == "warranty_months"
                    else round(rng.uniform(0.1, 15.0), 2)
                )
                session.add(
                    ProductAttributeValue(
                        product_id=product.id, attribute_id=attr.id, value_number=value_number
                    )
                )
            else:
                value_text = rng.choice(BRANDS) if attr.code == "brand" else rng.choice(COLORS)
                session.add(
                    ProductAttributeValue(
                        product_id=product.id, attribute_id=attr.id, value_text=value_text
                    )
                )

    await session.commit()
    logger.info("catalog seeded: %s products", settings.seed_products_count)
    return settings.seed_products_count
