import asyncio
import contextlib
import hashlib
import hmac
import json
import os

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.app.db.database import Base, get_db
from src.app.main import app
from src.app.models.onec_sync import OnecChangeLog  # noqa: F401
from src.app.models.user import RoleEnum, User
from src.app.utils.auth import create_access_token

# Используем отдельную тестовую БД, чтобы не трогать dev/prod данные
_env_url = os.getenv("DATABASE_URL", "")
if "postgresql" not in _env_url:
    raise RuntimeError(
        "Backend-тесты требуют postgresql DATABASE_URL. "
        "Запускай через `make test-backend` (поднимает docker-PG и задаёт env)."
    )
# Заменяем имя БД на promelectron_test
TEST_DATABASE_URL = _env_url.rsplit("/", 1)[0] + "/promelectron_test"


TEMPLATE_DB_NAME = "promelectron_test_template"


def make_settings(**overrides):
    """Фабрика тестовых Settings: копия глобального settings с переопределениями.

    Использует dataclasses.replace — новые поля Settings подхватываются
    автоматически, явный список полей в тестах больше не нужен.
    """
    import dataclasses

    from src.app.core.config import settings

    return dataclasses.replace(settings, **overrides)


WEBHOOK_TEST_SECRET = "test-secret"


@pytest.fixture
def signed_webhook(monkeypatch):
    """Вебхук ЮKassa с валидной HMAC-подписью (#210).

    Патчит settings в payment_service на копию с тестовым секретом и возвращает
    callable ``post(client, payload, secret=..., signature=None)``: подпись
    считается HMAC-SHA256 ровно по тем байтам, что уходят в запрос (content=,
    не json=). Передайте ``signature="..."`` для теста невалидной подписи.
    """
    patched = make_settings(yookassa_webhook_secret=WEBHOOK_TEST_SECRET)
    monkeypatch.setattr("src.app.services.payment_service.settings", patched)

    async def _post(client, payload, secret=WEBHOOK_TEST_SECRET, signature=None):
        raw = json.dumps(payload, ensure_ascii=False).encode()
        if signature is None:
            signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return await client.post(
            "/api/v1/payments/yookassa/webhook/",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-YooKassa-Signature": signature,
            },
        )

    return _post


async def make_product(session, *, price=None, price_type=None, **product_kwargs):
    """Создать Product + строку product_prices (site-вид по умолчанию).

    Цены больше не колонка products.price — тесты, которым нужен «товар с
    ценой», создают её через этот helper (price=Decimal(...) или None —
    бесценный товар без строки). Только flush, без commit — вызывающий код
    коммитит сам, как раньше.
    """
    from decimal import Decimal

    from src.app.core.config import settings
    from src.app.models.product import Product
    from src.app.models.product_price import ProductPrice

    product = Product(**product_kwargs)
    session.add(product)
    await session.flush()
    if price is not None:
        session.add(
            ProductPrice(
                product_id=product.id,
                price_type=price_type or settings.onec_site_price_type,
                price=Decimal(str(price)),
            )
        )
        await session.flush()
    return product


def _admin_url():
    return TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"


@pytest.fixture(autouse=True)
async def flush_redis(monkeypatch):
    """Flush Redis DB before each test to ensure cache isolation.
    
    If Redis is not available, mock it to avoid connection errors.
    """
    from src.app.core.redis_client import RedisClient

    class FakeRedis:
        _store: dict = {}

        async def flushdb(self):
            self._store.clear()

        async def get(self, key):
            return self._store.get(key)

        async def set(self, key, value):
            self._store[key] = value

        async def setex(self, key, ttl, value):
            self._store[key] = value

        async def delete(self, *keys):
            for key in keys:
                self._store.pop(key, None)

        async def scan_iter(self, match):
            for key in self._store:
                yield key

    # Check if Redis is available
    try:
        import redis.asyncio
        r = redis.asyncio.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        await r.ping()
        await r.close()
        redis_available = True
    except Exception:
        redis_available = False

    if not redis_available:
        fake = FakeRedis()
        monkeypatch.setattr(RedisClient, "get_instance", classmethod(lambda cls: fake))

    await RedisClient.flushdb()


@pytest.fixture(autouse=True)
def mock_storage_service(monkeypatch):
    """Mock storage service to avoid filesystem/MinIO side effects in tests."""

    class FakeStorage:
        async def upload(self, key, file):
            return f"/uploads/{key}"

        async def upload_raw(self, key, data, content_type, bucket=None):
            return f"/uploads/{key}"

        async def download_raw(self, key, bucket=None):
            raise FileNotFoundError(key)

        async def upload_image(self, key, file, content=None):
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


@pytest.fixture(autouse=True)
async def disable_real_email_sending(monkeypatch):
    """Disable real SMTP transport during tests.

    Email jobs are still enqueued so integration tests can verify job
    creation, but the actual aiosmtplib.send call is replaced to avoid
    hitting real mailboxes (e.g. test users with @example.com addresses).
    """
    async def _fake_send(*args, **kwargs):
        return "skipped:test_mock"

    monkeypatch.setattr(
        "src.app.services.email_service.send",
        _fake_send,
    )


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def _test_template_db():
    """Create a template database with schema for per-test DB cloning."""
    base_url = _admin_url()
    admin_engine = create_async_engine(
        base_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEMPLATE_DB_NAME}"'))
        await conn.execute(text(f'CREATE DATABASE "{TEMPLATE_DB_NAME}"'))
    await admin_engine.dispose()

    template_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + f"/{TEMPLATE_DB_NAME}"
    template_engine = create_async_engine(template_url, poolclass=NullPool)
    async with template_engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        await conn.run_sync(Base.metadata.create_all)
    await template_engine.dispose()

    yield TEMPLATE_DB_NAME

    admin_engine = create_async_engine(
        base_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEMPLATE_DB_NAME}"'))
    await admin_engine.dispose()


@pytest.fixture
async def test_engine(_test_template_db):
    """Provide an engine connected to a fresh per-test database."""
    base_url = _admin_url()
    db_name = f"promelectron_test_{uuid.uuid4().hex[:12]}"

    admin_engine = create_async_engine(
        base_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin_engine.connect() as conn:
        await conn.execute(
            text(f'CREATE DATABASE "{db_name}" TEMPLATE "{TEMPLATE_DB_NAME}"')
        )
    await admin_engine.dispose()

    db_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + f"/{db_name}"
    engine = create_async_engine(db_url, poolclass=NullPool)
    yield engine

    await engine.dispose()
    admin_engine = create_async_engine(
        base_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
    await admin_engine.dispose()


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
async def user_token(test_user):
    # F-10: sub is now the stable numeric user id, not email.
    return create_access_token(data={"sub": str(test_user.id), "role": test_user.role.value})


@pytest.fixture
async def admin_token(test_admin):
    # F-10: sub is now the stable numeric user id, not email.
    return create_access_token(data={"sub": str(test_admin.id), "role": test_admin.role.value})


@pytest.fixture
async def supplier_token(test_supplier_user_only):
    # F-10: sub is now the stable numeric user id, not email.
    return create_access_token(
        data={"sub": str(test_supplier_user_only.id), "role": test_supplier_user_only.role.value}
    )


@pytest.fixture
def cdek_delivery_payload():
    return {
        "tariff_code": 136,
        "delivery_mode": "PVZ",
        "delivery_point": "MSK123",
        "to_location": {"code": 44, "city": "Москва", "address": "Москва, ул. Ленина, д. 1"},
        "price": "350.00",
        "period_min": 2,
        "period_max": 4,
        "shipping_address": "Москва, ул. Ленина, д. 1",
    }


class _FakeCdekService:
    """Стаб CdekService для тестов создания заказа (gh-211, D-08).

    Подменяет module-level binding ``CdekService`` в ``order_service`` — НЕ
    атрибут класса, чтобы прямые тесты ``test_cdek.py`` (реальный
    ``calculate_delivery`` с моком ``CdekClient``) продолжали работать.
    Ответ согласован с фикстурой ``cdek_delivery_payload``.
    """

    @staticmethod
    async def calculate_delivery(db, items, supplier_id, to_location, delivery_point):
        from decimal import Decimal

        return [
            {
                "tariff_code": 136,
                "tariff_name": "Посылка склад-склад",
                "delivery_mode": "PVZ",
                "price": Decimal("350.00"),
                "period_min": 2,
                "period_max": 4,
            }
        ]

    @staticmethod
    async def cancel_cdek_order(cdek_uuid):
        return None


@pytest.fixture(autouse=True)
def mock_cdek_calculate(monkeypatch):
    """Блокирует реальные вызовы СДЭК из order_service во всех тестах (D-08).

    Тесты, которым нужно другое поведение (расхождение цены, CdekAPIError,
    недоступный tariff_code), переопределяют binding локально — их
    monkeypatch применяется после этой autouse-фикстуры и побеждает.
    """
    monkeypatch.setattr("src.app.services.order_service.CdekService", _FakeCdekService)


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

    product = await make_product(
        test_session,
        name="Test Product",
        description="Test product description",
        price="99.99",
        stock=10,
        category_id=test_category.id,
        supplier_id=supplier.id,
        is_active=True,
        weight_grams=500,
        length_cm=20,
        width_cm=15,
        height_cm=10,
    )
    await test_session.commit()
    await test_session.refresh(product)
    return product


@pytest.fixture
async def test_order(test_session, test_user, test_product):
    from src.app.models.cdek_order import CdekOrder
    from src.app.models.order import Order, OrderItem

    order = Order(
        user_id=test_user.id,
        total_price=99.99,
        status="pending",
        shipping_address="Москва, ул. Ленина, д. 1",
    )
    test_session.add(order)
    await test_session.flush()

    cdek_order = CdekOrder(
        order_id=order.id,
        tariff_code=136,
        delivery_mode="PVZ",
        delivery_point="MSK123",
        to_location={"code": 44, "city": "Москва", "address": "Москва, ул. Ленина, д. 1"},
        price=350.00,
        period_min=2,
        period_max=4,
    )
    test_session.add(cdek_order)
    await test_session.flush()

    order.cdek_order_id = cdek_order.id
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
    await test_session.refresh(order)
    return order


@pytest.fixture
async def admin_order(test_session, test_admin, test_product):
    """Order owned by the admin user for legacy status endpoint tests."""
    from src.app.models.cdek_order import CdekOrder
    from src.app.models.order import Order, OrderItem

    order = Order(
        user_id=test_admin.id,
        total_price=99.99,
        status="pending",
        shipping_address="Москва, ул. Ленина, д. 1",
    )
    test_session.add(order)
    await test_session.flush()

    cdek_order = CdekOrder(
        order_id=order.id,
        tariff_code=136,
        delivery_mode="PVZ",
        delivery_point="MSK123",
        to_location={"code": 44, "city": "Москва", "address": "Москва, ул. Ленина, д. 1"},
        price=350.00,
        period_min=2,
        period_max=4,
    )
    test_session.add(cdek_order)
    await test_session.flush()

    order.cdek_order_id = cdek_order.id
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
    await test_session.refresh(order)
    return order


@pytest.fixture
async def onec_mock_server():
    """Run the mock 1C OData server on a free port and return its base URL."""
    import uvicorn

    from tests.mocks.onec_server import app as onec_app

    config = uvicorn.Config(onec_app, host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    try:
        while not server.started:
            await asyncio.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
