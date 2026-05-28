import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.app.db.database import Base, get_db
from src.app.main import app
from src.app.models.user import RoleEnum, User
from src.app.utils.auth import create_access_token

# Используем отдельную тестовую БД, чтобы не трогать dev/prod данные
_env_url = os.getenv("DATABASE_URL", "")
if "postgresql" in _env_url:
    # Заменяем имя БД на promelectron_test
    TEST_DATABASE_URL = _env_url.rsplit("/", 1)[0] + "/promelectron_test"
else:
    TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(autouse=True)
async def flush_redis():
    """Flush Redis DB before each test to ensure cache isolation."""
    from src.app.core.redis_client import redis_client

    await redis_client.flushdb()


@pytest.fixture(autouse=True)
def mock_storage_service(monkeypatch):
    """Mock storage service to avoid filesystem/MinIO side effects in tests."""

    class FakeStorage:
        async def upload(self, key, file):
            return f"/uploads/{key}"

        async def upload_image(self, key, file):
            base, _ = os.path.splitext(key)
            return {
                "original": f"/uploads/{key}",
                "small": f"/uploads/{base}_small.webp",
                "medium": f"/uploads/{base}_medium.webp",
                "large": f"/uploads/{base}_large.webp",
            }

        def get_url(self, key):
            return f"/uploads/{key}"

        async def delete(self, key):
            pass

        async def delete_image(self, key):
            pass

    fake = FakeStorage()
    monkeypatch.setattr("src.app.api.products.storage", fake)
    monkeypatch.setattr("src.app.api.users.storage", fake)
    monkeypatch.setattr("src.app.main.storage", fake)
    monkeypatch.setattr("src.app.services.storage_service.storage", fake)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    # Для PostgreSQL: создаём тестовую БД если не существует
    if "postgresql" in TEST_DATABASE_URL:
        db_name = TEST_DATABASE_URL.rsplit("/", 1)[-1]
        base_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
        admin_engine = create_async_engine(base_url, isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            )
            if not result.scalar():
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        await admin_engine.dispose()

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(test_session):
    from src.app.utils.rate_limiter import limiter

    limiter.reset()

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def user_token():
    return create_access_token(data={"sub": "testuser@example.com"})


@pytest.fixture
def admin_token():
    return create_access_token(data={"sub": "admin@example.com"})


@pytest.fixture
def supplier_token():
    return create_access_token(data={"sub": "supplier@example.com"})


@pytest.fixture
async def test_user(test_session):
    from src.app.utils.auth import hash_password

    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("password123"),
        role=RoleEnum.user,
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(test_session):
    from src.app.utils.auth import hash_password

    user = User(
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        role=RoleEnum.admin,
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def test_supplier_user_only(test_session):
    """User with supplier role, but no Supplier record."""
    from src.app.utils.auth import hash_password

    user = User(
        email="supplier@example.com",
        hashed_password=hash_password("supplier123"),
        role=RoleEnum.supplier,
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def test_supplier(test_session, test_supplier_user_only):
    from src.app.models.supplier import Supplier

    supplier = Supplier(
        user_id=test_supplier_user_only.id,
        name="Test Supplier",
        description="Test supplier",
        api_key="test-api-key-123",
        is_active=True,
    )
    test_session.add(supplier)
    await test_session.commit()
    await test_session.refresh(supplier)
    return test_supplier_user_only


@pytest.fixture
async def test_category(test_session):
    from src.app.models.category import Category

    category = Category(name="Test Category", description="Test category description")
    test_session.add(category)
    await test_session.commit()
    await test_session.refresh(category)
    return category


@pytest.fixture
async def test_product(test_session, test_supplier, test_category):
    from src.app.models.product import Product
    from src.app.models.supplier import Supplier

    # test_supplier уже создал Supplier, находим его
    result = await test_session.execute(
        select(Supplier).where(Supplier.user_id == test_supplier.id)
    )
    supplier = result.scalars().first()
    if not supplier:
        supplier = Supplier(
            user_id=test_supplier.id,
            name="Test Supplier",
            description="Test supplier",
            api_key="test-api-key-123",
            is_active=True,
        )
        test_session.add(supplier)
        await test_session.commit()
        await test_session.refresh(supplier)

    product = Product(
        name="Test Product",
        description="Test product description",
        price=99.99,
        stock=10,
        category_id=test_category.id,
        supplier_id=supplier.id,
        is_active=True,
    )
    test_session.add(product)
    await test_session.commit()
    await test_session.refresh(product)
    return product


@pytest.fixture
async def test_order(test_session, test_user, test_product):
    from src.app.models.order import Order, OrderItem

    order = Order(
        user_id=test_user.id,
        total_price=99.99,
        status="pending",
        shipping_address="Москва, ул. Ленина, д. 1",
    )
    test_session.add(order)
    await test_session.commit()
    await test_session.refresh(order)

    order_item = OrderItem(
        order_id=order.id,
        product_id=test_product.id,
        quantity=1,
        price_at_time=99.99,
    )
    test_session.add(order_item)
    await test_session.commit()
    return order
