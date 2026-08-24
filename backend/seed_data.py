import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
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
from src.app.services.price_service import upsert_product_price
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
    "cdek_shipment_point": "44",
    "sender_name": "Тестовый поставщик",
    "sender_phone": "+79990001122",
}

# Электрокаталог (H001=C, issue #147): согласован с seed мока 1С
# (mocks/onec-server/src/onec_mock/seed.py). Категории — плоские корневые;
# get_or_create по имени переиспользует категории, уже созданные intake мока
# на test-стенде («Розетки»/«Выключатели» там дочерние, но матч по имени —
# дубликатов не будет). Имена товаров намеренно отличаются от шаблонов мока,
# чтобы не пересекаться с его 30 SKU (SKU мока: EL-*).
TEST_CATEGORIES: list[dict[str, str]] = [
    {"name": "Розетки", "description": "Розетки силовые и слаботочные."},
    {"name": "Выключатели", "description": "Выключатели и переключатели."},
    {"name": "Кабель и провод", "description": "Кабели силовые и провода монтажные."},
    {"name": "Защита и автоматика", "description": "Автоматические выключатели, УЗО и дифавтоматы."},
    {"name": "Освещение", "description": "Светильники и лампы."},
    {"name": "Щитовое оборудование", "description": "Боксы, DIN-рейка и клеммы."},
]

TEST_PRODUCTS: list[dict[str, Any]] = [
    {
        "name": "Розетка Legrand Valena Life 2P+E с заземлением белая",
        "description": "Розетка скрытого монтажа с заземляющим контактом, 16А 250В.",
        "price": 450.0,
        "stock": 40,
        "category_name": "Розетки",
    },
    {
        "name": "Розетка компьютерная Schneider Electric Sedna RJ45 кат.6 белая",
        "description": "Розетка RJ45 категории 6 для структурированных кабельных сетей.",
        "price": 890.0,
        "stock": 25,
        "category_name": "Розетки",
    },
    {
        "name": "Выключатель ABB Basic55 одноклавишный с рамкой белый",
        "description": "Одноклавишный выключатель скрытого монтажа, 10А 250В.",
        "price": 620.0,
        "stock": 30,
        "category_name": "Выключатели",
    },
    {
        "name": "Переключатель проходной EKF PROxima двухклавишный слоновая кость",
        "description": "Двухклавишный проходной переключатель для управления из двух мест.",
        "price": 1150.0,
        "stock": 15,
        "category_name": "Выключатели",
    },
    {
        "name": "Кабель ВВГнг-LS 3×1.5 ГОСТ 31996-2012 (бухта 100 м)",
        "description": "Силовой кабель с медными жилами, не распространяющий горение, бухта 100 м.",
        "price": 7800.0,
        "stock": 12,
        "category_name": "Кабель и провод",
    },
    {
        "name": "Провод ПВ-3 1×2.5 жёлто-зелёный (м)",
        "description": "Монтажный провод с медной многопроволочной жилой, цена за метр.",
        "price": 65.0,
        "stock": 500,
        "category_name": "Кабель и провод",
    },
    {
        "name": "Автомат IEK ВА47-29 1P 16A характеристика C",
        "description": "Модульный автоматический выключатель 4.5кА, характеристика C.",
        "price": 320.0,
        "stock": 60,
        "category_name": "Защита и автоматика",
    },
    {
        "name": "УЗО ABB FH202 AC-40/0,03 2P 40A",
        "description": "Выключатель дифференциального тока 2P 40A 30мА тип AC.",
        "price": 3450.0,
        "stock": 10,
        "category_name": "Защита и автоматика",
    },
    {
        "name": "Светильник накладной LED Юпитер Standard 24Вт IP44 4000K",
        "description": "Накладной светодиодный светильник для влажных помещений.",
        "price": 1890.0,
        "stock": 20,
        "category_name": "Освещение",
    },
    {
        "name": "Бокс IEK ЩРН-П-12 IP41 навесной пластиковый",
        "description": "Навесной пластиковый бокс на 12 модулей с прозрачной дверцей.",
        "price": 950.0,
        "stock": 18,
        "category_name": "Щитовое оборудование",
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
        # Обновляем CDEK-поля на случай изменений в тестовых данных
        for field, value in TEST_SUPPLIER.items():
            setattr(supplier, field, value)
        logger.info(f"Поставщик уже существует: {supplier.name}")
        return supplier

    # Если нет — ищем по api_key
    result = await session.execute(
        select(Supplier).where(Supplier.api_key == TEST_SUPPLIER["api_key"])
    )
    supplier = result.scalar_one_or_none()
    if supplier:
        for field, value in TEST_SUPPLIER.items():
            setattr(supplier, field, value)
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
        # name не unique: на test-стенде возможны дубли от 1C-intake — берём первую
        category = result.scalars().first()
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
        # name не unique: возможны дубли — берём первый найденный
        existing_product = result.scalars().first()
        if existing_product:
            logger.info(f"Товар уже существует, пропускаю: {existing_product.name}")
            continue

        category = categories_map[payload["category_name"]]
        now = datetime.now(timezone.utc)
        product = Product(
            name=payload["name"],
            description=payload["description"],
            stock=payload["stock"],
            category_id=category.id,
            supplier_id=supplier.id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(product)
        await session.flush()
        # Цены живут в product_prices (сайтовый вид), products.price больше нет
        await upsert_product_price(
            session, product.id, settings.onec_site_price_type, Decimal(str(payload["price"]))
        )
        logger.info(f"Добавлен товар: {product.name}")


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
            await get_or_create_admin_user(session)
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
