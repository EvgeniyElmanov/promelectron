import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.database import SessionLocal
from src.app.models.cart import Cart, CartItem
from src.app.models.category import Category
from src.app.models.favorite import Favorite
from src.app.models.notification import Notification
from src.app.models.order import Order, OrderItem
from src.app.models.payment import Payment
from src.app.models.product import Product
from src.app.models.review import Review
from src.app.models.supplier import Supplier
from src.app.models.user import RoleEnum, User
from src.app.utils.auth import hash_password

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


TEST_ADMIN_USER: dict[str, Any] = {
    "email": "seed-admin@example.com",
    "password": "seedpassword123",
    "full_name": "Тестовый Админ",
    "role": RoleEnum.admin,
    "is_active": True,
}

TEST_SUPPLIER_USER: dict[str, Any] = {
    "email": "seed-supplier@example.com",
    "password": "seedpassword123",
    "full_name": "Тестовый поставщик",
    "role": RoleEnum.supplier,
    "is_active": True,
}

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


async def get_or_create_admin_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == TEST_ADMIN_USER["email"]))
    user = result.scalar_one_or_none()
    if user:
        if user.role != RoleEnum.admin:
            user.role = RoleEnum.admin
            user.is_active = True
            await session.flush()
            logger.info(f"Обновлён пользователь-админ: {user.email} (роль -> admin)")
        else:
            logger.info(f"Пользователь-админ уже существует: {user.email}")
        return user

    user = User(
        email=TEST_ADMIN_USER["email"],
        hashed_password=hash_password(TEST_ADMIN_USER["password"]),
        full_name=TEST_ADMIN_USER["full_name"],
        role=TEST_ADMIN_USER["role"],
        is_active=TEST_ADMIN_USER["is_active"],
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.flush()
    logger.info(f"Создан пользователь-админ: {user.email}")
    return user


async def get_or_create_supplier_user(session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == TEST_SUPPLIER_USER["email"]))
    user = result.scalar_one_or_none()
    if user:
        if user.role != RoleEnum.supplier:
            user.role = RoleEnum.supplier
            user.is_active = True
            await session.flush()
            logger.info(f"Обновлён пользователь-поставщик: {user.email} (роль -> supplier)")
        else:
            logger.info(f"Пользователь-поставщик уже существует: {user.email}")
        return user

    user = User(
        email=TEST_SUPPLIER_USER["email"],
        hashed_password=hash_password(TEST_SUPPLIER_USER["password"]),
        full_name=TEST_SUPPLIER_USER["full_name"],
        role=TEST_SUPPLIER_USER["role"],
        is_active=TEST_SUPPLIER_USER["is_active"],
        created_at=datetime.now(timezone.utc),
    )
    session.add(user)
    await session.flush()
    logger.info(f"Создан пользователь-поставщик: {user.email}")
    return user


async def get_or_create_supplier(session: AsyncSession, user: User) -> Supplier:
    # Сначала ищем по user_id (уникальный constraint)
    result = await session.execute(select(Supplier).where(Supplier.user_id == user.id))
    supplier = result.scalar_one_or_none()
    if supplier:
        logger.info(f"Поставщик уже существует: {supplier.name}")
        return supplier

    # Если нет — ищем по api_key
    result = await session.execute(
        select(Supplier).where(Supplier.api_key == TEST_SUPPLIER["api_key"])
    )
    supplier = result.scalar_one_or_none()
    if supplier:
        logger.info(f"Поставщик уже существует: {supplier.name}")
        return supplier

    supplier = Supplier(
        user_id=user.id,
        **TEST_SUPPLIER,
        created_at=datetime.now(timezone.utc),
    )
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
            category = Category(**payload, created_at=datetime.now(timezone.utc))
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
        now = datetime.now(timezone.utc)
        product = Product(
            name=payload["name"],
            description=payload["description"],
            price=payload["price"],
            stock=payload["stock"],
            category_id=category.id,
            supplier_id=supplier.id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(product)
        logger.info(f"Добавлен товар: {product.name}")


from sqlalchemy import delete

async def cleanup_e2e_artifacts(session: AsyncSession) -> None:
    """Delete categories and products created by e2e tests (name starts with 'E2E')."""
    e2e_products = (await session.execute(
        select(Product).where(Product.name.like("E2E%"))
    )).scalars().all()
    for p in e2e_products:
        await session.delete(p)
        logger.info(f"Удалён e2e товар: {p.name}")

    e2e_categories = (await session.execute(
        select(Category).where(Category.name.like("E2E%"))
    )).scalars().all()
    for c in e2e_categories:
        await session.delete(c)
        logger.info(f"Удалена e2e категория: {c.name}")

    await session.flush()


async def reset_test_state(session: AsyncSession) -> None:
    """Reset mutable state between E2E test runs."""
    # Delete test-generated data in dependency order
    await session.execute(delete(Review))
    await session.execute(delete(Favorite))
    await session.execute(delete(Notification))
    await session.execute(delete(Payment))
    await session.execute(delete(OrderItem))
    await session.execute(delete(Order))
    await session.execute(delete(CartItem))
    await session.execute(delete(Cart))
    # Reset product stock to seed values
    stock_map = {p["name"]: p["stock"] for p in TEST_PRODUCTS}
    for name, stock in stock_map.items():
        await session.execute(
            Product.__table__.update().where(Product.name == name).values(stock=stock)
        )
    await session.flush()
    logger.info("Test state reset completed")


async def seed_data() -> None:
    async with SessionLocal() as session:
        try:
            await cleanup_e2e_artifacts(session)
            await reset_test_state(session)
            admin_user = await get_or_create_admin_user(session)
            supplier_user = await get_or_create_supplier_user(session)
            supplier = await get_or_create_supplier(session, supplier_user)
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
