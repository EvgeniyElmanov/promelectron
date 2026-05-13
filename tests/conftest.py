import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from server.app.db.database import Base, get_db
from server.app.main import app
from server.app.models.user import RoleEnum, User
from server.app.utils.auth import create_access_token


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
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
    from server.app.utils.auth import hash_password

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
    from server.app.utils.auth import hash_password

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
async def test_supplier(test_session):
    from server.app.utils.auth import hash_password

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
async def test_category(test_session):
    from server.app.models.category import Category

    category = Category(name="Test Category", description="Test category description")
    test_session.add(category)
    await test_session.commit()
    await test_session.refresh(category)
    return category


@pytest.fixture
async def test_product(test_session, test_supplier, test_category):
    from server.app.models.product import Product
    from server.app.models.supplier import Supplier

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
