"""Фикстуры тестов OData-мока: Docker-PG, схема onec_test, маленькие синтетические данные.

Сид (onec_seed.sql.gz) в тестах НЕ используется — только синтетика.
"""

import asyncio
import os

os.environ.setdefault("ONEC_MOCK_SCHEMA", "onec_test")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron"
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from onec_mock.config import settings  # noqa: E402
from onec_mock.main import app  # noqa: E402

SCHEMA = settings.onec_mock_schema

CAT1 = "11111111-1111-1111-1111-111111111111"
CAT2 = "22222222-2222-2222-2222-222222222222"
UNIT1 = "33333333-3333-3333-3333-333333333333"
PT_RETAIL = "44444444-4444-4444-4444-444444444444"
PT_OPT = "55555555-5555-5555-5555-555555555555"
P1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
P2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
P3_FOLDER = "cccccccc-cccc-cccc-cccc-cccccccccccc"
P4_SERVICE = "dddddddd-dddd-dddd-dddd-dddddddddddd"
WH1 = "66666666-6666-6666-6666-666666666666"
ORG1 = "77777777-7777-7777-7777-777777777777"
ATTR1 = "88888888-8888-8888-8888-888888888888"
ATTR2 = "12121212-1212-1212-1212-121212121212"
VAL1 = "99999999-9999-9999-9999-999999999999"
F1 = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
F2 = "ffffffff-ffff-ffff-ffff-ffffffffffff"

AUTH = (settings.login, settings.password)

DDL = f"""
DROP SCHEMA IF EXISTS {SCHEMA} CASCADE;
CREATE SCHEMA {SCHEMA};
CREATE TABLE {SCHEMA}.categories (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    ref_key text PRIMARY KEY, description text NOT NULL, deletion_mark boolean NOT NULL DEFAULT false
);
CREATE TABLE {SCHEMA}.products (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    ref_key text PRIMARY KEY, parent_key text NOT NULL DEFAULT '', is_folder boolean NOT NULL DEFAULT false,
    description text NOT NULL, full_name text NOT NULL DEFAULT '', code text NOT NULL DEFAULT '',
    article text NOT NULL DEFAULT '', product_type text NOT NULL DEFAULT '',
    category_key text NOT NULL DEFAULT '', unit_key text NOT NULL DEFAULT '',
    deletion_mark boolean NOT NULL DEFAULT false
);
CREATE TABLE {SCHEMA}.units (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    ref_key text PRIMARY KEY, description text NOT NULL DEFAULT '', code text NOT NULL DEFAULT ''
);
CREATE TABLE {SCHEMA}.price_types (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    ref_key text PRIMARY KEY, description text NOT NULL DEFAULT '',
    deletion_mark boolean NOT NULL DEFAULT false
);
CREATE TABLE {SCHEMA}.prices (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    period timestamptz, price_type_key text, product_key text, characteristic_key text,
    price numeric(15,2), is_actual boolean
);
CREATE TABLE {SCHEMA}.stock_balance (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    organization_key text NOT NULL, product_key text NOT NULL, warehouse_key text NOT NULL,
    quantity numeric(15,3) NOT NULL DEFAULT 0
);
CREATE TABLE {SCHEMA}.attribute_definitions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    ref_key text PRIMARY KEY, description text NOT NULL DEFAULT '',
    deletion_mark boolean NOT NULL DEFAULT false, raw jsonb
);
CREATE TABLE {SCHEMA}.attribute_values (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    ref_key text PRIMARY KEY, description text NOT NULL DEFAULT '', owner_key text NOT NULL DEFAULT '',
    deletion_mark boolean NOT NULL DEFAULT false
);
CREATE TABLE {SCHEMA}.product_attributes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    product_key text NOT NULL, line_number integer NOT NULL, attribute_key text NOT NULL,
    value_key text NOT NULL DEFAULT '', text_value text NOT NULL DEFAULT ''
);
CREATE TABLE {SCHEMA}.product_files (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    ref_key text PRIMARY KEY, product_key text NOT NULL, description text NOT NULL DEFAULT '',
    extension text NOT NULL DEFAULT '', file_size integer NOT NULL DEFAULT 0,
    deletion_mark boolean NOT NULL DEFAULT false, synced_at timestamptz NOT NULL DEFAULT now()
);
"""

SEED = f"""
INSERT INTO {SCHEMA}.categories (ref_key, description, deletion_mark) VALUES
    ('{CAT1}', 'Кабель', false), ('{CAT2}', 'Крепеж', true);
INSERT INTO {SCHEMA}.units (ref_key, description, code) VALUES ('{UNIT1}', 'шт', '796 ');
INSERT INTO {SCHEMA}.price_types (ref_key, description, deletion_mark) VALUES
    ('{PT_RETAIL}', 'Розница', false), ('{PT_OPT}', 'Оптовая', false);
INSERT INTO {SCHEMA}.products
    (ref_key, parent_key, is_folder, description, full_name, code, article, product_type,
     category_key, unit_key, deletion_mark) VALUES
    ('{P1}', '', false, 'Кабель ВВГ 2х1.5', 'Кабель ВВГ 2х1.5 полное', 'НФ-00000001', '25-211',
     'Запас', '{CAT1}', '{UNIT1}', false),
    ('{P2}', '', false, 'Дюбель 6х40', 'Дюбель 6х40 полное', 'НФ-00000002', 'Д-640',
     'Запас', '{CAT2}', '{UNIT1}', false),
    ('{P3_FOLDER}', '', true, 'Папка товаров', '', 'НФ-00000003', '', 'Запас', '', '', false),
    ('{P4_SERVICE}', '', false, 'Доставка', 'Доставка', 'НФ-00000004', '', 'Услуга', '', '', false);
INSERT INTO {SCHEMA}.prices
    (period, price_type_key, product_key, characteristic_key, price, is_actual) VALUES
    ('2025-03-01T00:00:00', '{PT_RETAIL}', '{P1}', '', 280.00, true),
    ('2025-03-01T00:00:00', '{PT_OPT}', '{P1}', '', 240.00, true),
    ('2025-03-01T00:00:00', '{PT_RETAIL}', '{P2}', '', 3.50, true);
INSERT INTO {SCHEMA}.stock_balance (organization_key, product_key, warehouse_key, quantity) VALUES
    ('{ORG1}', '{P1}', '{WH1}', 10.5),
    ('{ORG1}', '{P2}', '{WH1}', -2);
-- 25 строк с одинаковыми organization_key/warehouse_key: ловушка неуникальной сортировки
-- при постраничном обходе (регрессионный тест пагинации)
INSERT INTO {SCHEMA}.stock_balance (organization_key, product_key, warehouse_key, quantity)
SELECT '{ORG1}', 'aaaa0000-0000-0000-0000-' || lpad(g::text, 12, '0'), '{WH1}', g
FROM generate_series(1, 25) AS g;
INSERT INTO {SCHEMA}.attribute_definitions (ref_key, description, deletion_mark, raw) VALUES
    ('{ATTR1}', 'Цвет', false, '{{"Ref_Key": "{ATTR1}", "Description": "Цвет", "Заголовок": "Цвет товара",
      "ValueType": {{"Types": ["CatalogRef.ЗначенияСвойствОбъектов"]}}}}'::jsonb),
    ('{ATTR2}', 'Материал', false, NULL);
INSERT INTO {SCHEMA}.attribute_values (ref_key, description, owner_key, deletion_mark) VALUES
    ('{VAL1}', 'Красный', '{ATTR1}', false);
INSERT INTO {SCHEMA}.product_attributes
    (product_key, line_number, attribute_key, value_key, text_value) VALUES
    ('{P1}', 1, '{ATTR1}', '{VAL1}', ''),
    ('{P1}', 2, '{ATTR1}', '', 'произвольный текст');
INSERT INTO {SCHEMA}.product_files
    (ref_key, product_key, description, extension, file_size, deletion_mark, synced_at) VALUES
    ('{F1}', '{P1}', 'photo1', 'jpg', 123807, false, '2021-04-13T14:20:02'),
    ('{F2}', '{P2}', 'photo2', 'png', 500, false, '2021-04-14T10:00:00');
"""


async def _setup_db() -> None:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as conn:
            for statement in (DDL + SEED).split(";"):
                if statement.strip():
                    await conn.execute(text(statement))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    asyncio.run(_setup_db())


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://onec-mock:8100") as c:
        yield c
