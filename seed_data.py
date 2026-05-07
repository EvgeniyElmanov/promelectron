import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.db.database import SessionLocal
from server.app.models.category import Category
from server.app.models.product import Product
from server.app.models.supplier import Supplier


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.utcnow()


TEST_SUPPLIER: dict[str, Any] = {
    "name": "Тестовый поставщик",
    "description": "Поставщик для заполнения витрины магазина тестовыми товарами.",
    "api_key": "seed-supplier-api-key",
    "is_active": True,
}

TEST_CATEGORIES: list[dict[str, str]] = [
    {"name": "Смартфоны", "description": "Мобильные телефоны и смартфоны."},
    {"name": "Ноутбуки", "description": "Ноутбуки для работы и развлечений."},
    {"name": "Аксессуары", "description": "Полезные аксессуары для техники."},
]

TEST_PRODUCTS: list[dict[str, Any]] = [
    {
        "name": "Смартфон Nova X12",
        "description": "Мощный смартфон с AMOLED-экраном 6.7 дюйма и батареей 5000 мАч.",
        "price": 45990.0,
        "stock": 18,
        "category_name": "Смартфоны",
    },
    {
        "name": "Смартфон PixelOne Lite",
        "description": "Компактный смартфон с качественной камерой и чистой операционной системой.",
        "price": 28990.0,
        "stock": 24,
        "category_name": "Смартфоны",
    },
    {
        "name": "Ноутбук Orion Pro 14",
        "description": "Легкий ноутбук для работы: 16 ГБ RAM, SSD 512 ГБ, металлический корпус.",
        "price": 89990.0,
        "stock": 9,
        "category_name": "Ноутбуки",
    },
    {
        "name": "Ноутбук Falcon Air 15",
        "description": "Универсальный ноутбук с IPS-экраном 15.6 дюйма и длительным временем работы.",
        "price": 73990.0,
        "stock": 11,
        "category_name": "Ноутбуки",
    },
    {
        "name": "Беспроводные наушники SoundBeat S3",
        "description": "Наушники с активным шумоподавлением и автономностью до 30 часов.",
        "price": 11990.0,
        "stock": 35,
        "category_name": "Аксессуары",
    },
]


async def get_or_create_supplier(session: AsyncSession) -> Supplier:
    result = await session.execute(
        select(Supplier).where(Supplier.api_key == TEST_SUPPLIER["api_key"])
    )
    supplier = result.scalar_one_or_none()
    if supplier:
        logger.info(f"Поставщик уже существует: {supplier.name}")
        return supplier

    supplier = Supplier(**TEST_SUPPLIER, created_at=utcnow_naive())
    session.add(supplier)
    await session.flush()
    logger.info(f"Создан поставщик: {supplier.name}")
    return supplier


async def get_or_create_categories(session: AsyncSession) -> dict[str, Category]:
    categories_map: dict[str, Category] = {}
    for payload in TEST_CATEGORIES:
        result = await session.execute(select(Category).where(Category.name == payload["name"]))
        category = result.scalar_one_or_none()
        if category:
            logger.info(f"Категория уже существует: {category.name}")
        else:
            category = Category(**payload, created_at=utcnow_naive())
            session.add(category)
            await session.flush()
            logger.info(f"Создана категория: {category.name}")
        categories_map[payload["name"]] = category
    return categories_map


async def create_products(
    session: AsyncSession,
    supplier: Supplier,
    categories_map: dict[str, Category],
) -> None:
    logger.info("Создаю товары...")
    for payload in TEST_PRODUCTS:
        result = await session.execute(select(Product).where(Product.name == payload["name"]))
        existing_product = result.scalar_one_or_none()
        if existing_product:
            logger.info(f"Товар уже существует, пропускаю: {existing_product.name}")
            continue

        category = categories_map[payload["category_name"]]
        product = Product(
            name=payload["name"],
            description=payload["description"],
            price=payload["price"],
            stock=payload["stock"],
            category_id=category.id,
            supplier_id=supplier.id,
            is_active=True,
            created_at=utcnow_naive(),
            updated_at=utcnow_naive(),
        )
        session.add(product)
        logger.info(f"Добавлен товар: {product.name}")


async def seed_data() -> None:
    async with SessionLocal() as session:
        try:
            supplier = await get_or_create_supplier(session)
            categories_map = await get_or_create_categories(session)
            await create_products(session, supplier, categories_map)
            await session.commit()
            logger.info("Готово!")
        except Exception:
            await session.rollback()
            logger.exception("Ошибка при заполнении тестовыми данными.")
            raise


def main() -> None:
    asyncio.run(seed_data())


if __name__ == "__main__":
    main()
