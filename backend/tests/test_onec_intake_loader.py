"""Тесты загрузчика intake-файлов onec_intake_loader (Фаза 4, #120).

Покрывает Acceptance Criteria:
- повторный разбор одного файла → 0 новых записей, 0 ошибок;
- DeletionMark=true → is_active=false;
- «Сечение 10,0мм2» → value_number=10.0, unit=мм² в справочнике;
- broken payload → status failed + error;
- enqueue SEARCH_INDEX_PRODUCTS на затронутые товары.
"""

import hashlib
import io
import json
import zipfile
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from src.app.models.attribute import Attribute, ProductAttributeValue
from src.app.models.category import Category
from src.app.models.job import Job
from src.app.models.onec_sync import OnecIntakeLog
from src.app.models.product import Product
from src.app.models.supplier import Supplier
from src.app.services.onec_intake_loader import process_intake
from tests.conftest import make_product

GUID_PRODUCT_1 = "11111111-1111-1111-1111-111111111111"
GUID_PRODUCT_2 = "22222222-2222-2222-2222-222222222222"
GUID_PRODUCT_DEL = "33333333-3333-3333-3333-333333333333"
GUID_CATEGORY = "44444444-4444-4444-4444-444444444444"
GUID_ATTR_SECTION = "d62aec37-7c07-11eb-80d5-00155d006601"
GUID_PRICE_TYPE = "3d3bea35-5d6a-11eb-948a-f81a67046005"


class FakeStorage:
    """In-memory storage: ключ → bytes (контракт download_raw из #120)."""

    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, bucket: str, key: str, data: bytes) -> None:
        self.objects[(bucket, key)] = data

    async def download_raw(self, key: str, bucket: str | None = None) -> bytes:
        try:
            return self.objects[(bucket or "onec-intake", key)]
        except KeyError:
            raise FileNotFoundError(key) from None


@pytest.fixture
def fake_storage(monkeypatch):
    storage = FakeStorage()
    monkeypatch.setattr("src.app.services.onec_intake_loader.storage", storage)
    return storage


@pytest.fixture
async def supplier_id(test_session, test_supplier):
    result = await test_session.execute(
        select(Supplier).where(Supplier.user_id == test_supplier.id)
    )
    return result.scalar_one().id


@pytest.fixture
def patched_settings(monkeypatch, supplier_id):
    """settings с ONEC_DEFAULT_SUPPLIER_ID и сайтовым видом цены GUID_PRICE_TYPE."""
    from tests.conftest import make_settings

    patched = make_settings(
        onec_default_supplier_id=supplier_id,
        onec_site_price_type=GUID_PRICE_TYPE,
    )
    monkeypatch.setattr("src.app.services.onec_intake_loader.settings", patched)
    # helpers цены читают settings в своём модуле
    monkeypatch.setattr("src.app.services.price_service.settings", patched)
    return patched


async def _price_of(session, product_id: int, price_type: str = GUID_PRICE_TYPE):
    """Цена товара из product_prices по виду (site-выражение в тестах не читаем —
    column_property привязан к глобальному settings.onec_site_price_type)."""
    from decimal import Decimal

    from src.app.models.product_price import ProductPrice

    result = await session.execute(
        select(ProductPrice.price).where(
            ProductPrice.product_id == product_id,
            ProductPrice.price_type == price_type,
        )
    )
    value = result.scalar_one_or_none()
    return Decimal(value) if value is not None else None


async def _make_intake(test_session, fake_storage, payload: bytes, key: str | None = None) -> str:
    key = key or f"2026/07/31/test_{uuid4().hex[:8]}.bin"
    fake_storage.put("onec-intake", key, payload)
    log = OnecIntakeLog(
        bucket="onec-intake",
        object_key=key,
        content_type="application/octet-stream",
        received_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        status="received",
    )
    test_session.add(log)
    await test_session.commit()
    await test_session.refresh(log)
    return str(log.intake_id)


def _odata(entity: str, records: list[dict]) -> bytes:
    return json.dumps(
        {"odata.metadata": f"http://1c/odata/$metadata#{entity}", "value": records},
        ensure_ascii=False,
    ).encode()


def _cml_zip(import_xml: str, offers_xml: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("import.xml", import_xml)
        archive.writestr("offers.xml", offers_xml)
    return buffer.getvalue()


def _products_payload() -> bytes:
    return _odata(
        "Catalog_Номенклатура",
        [
            {
                "Ref_Key": GUID_PRODUCT_1,
                "Description": "Кабель ВВГнг 3х2,5",
                "НаименованиеПолное": "Кабель ВВГнг(А)-LS 3х2,5",
                "Артикул": "KB-001",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
                "Вес": 0.5,
                "КатегорияНоменклатуры_Key": GUID_CATEGORY,
            },
            {
                "Ref_Key": GUID_PRODUCT_2,
                "Description": "Кабель ВВГнг 3х1,5",
                "Артикул": "KB-002",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
                "Вес": 0,
            },
            {
                "Ref_Key": "55555555-5555-5555-5555-555555555555",
                "Description": "Папка каталога",
                "IsFolder": True,
                "DeletionMark": False,
            },
            {
                "Ref_Key": "66666666-6666-6666-6666-666666666666",
                "Description": "Доставка",
                "ТипНоменклатуры": "Услуга",
                "IsFolder": False,
                "DeletionMark": False,
            },
        ],
    )


# ─── OData: товары ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_odata_products_upsert(
    test_session, fake_storage, patched_settings
):
    intake_id = await _make_intake(test_session, fake_storage, _products_payload())

    stats = await process_intake(test_session, intake_id)

    assert stats.products_created == 2
    assert stats.skipped == 2  # папка + услуга не загружаются
    assert not stats.errors

    result = await test_session.execute(
        select(Product).where(Product.onec_id == GUID_PRODUCT_1)
    )
    product = result.scalar_one()
    assert product.name == "Кабель ВВГнг 3х2,5"
    assert product.sku == "KB-001"
    assert product.weight_grams == 500
    # F003: до прихода первой валидной цены товар не виден в каталоге
    assert product.is_active is False
    assert product.supplier_id == patched_settings.onec_default_supplier_id

    log = await test_session.get(OnecIntakeLog, (await test_session.execute(
        select(OnecIntakeLog.id).where(OnecIntakeLog.intake_id == intake_id)
    )).scalar_one())
    assert log.status == "parsed"
    assert log.error is None


@pytest.mark.asyncio
async def test_loader_idempotent_reparse(
    test_session, fake_storage, patched_settings
):
    """AC: повторный разбор одного файла → 0 новых записей, 0 ошибок."""
    payload = _products_payload()
    intake_id = await _make_intake(test_session, fake_storage, payload)

    await process_intake(test_session, intake_id)
    count_after_first = (
        await test_session.execute(select(func.count()).select_from(Product))
    ).scalar_one()

    stats = await process_intake(test_session, intake_id)
    count_after_second = (
        await test_session.execute(select(func.count()).select_from(Product))
    ).scalar_one()

    assert stats.products_created == 0
    assert not stats.errors
    assert count_after_second == count_after_first


@pytest.mark.asyncio
async def test_loader_deletion_mark_soft_deletes(
    test_session, fake_storage, patched_settings
):
    """AC: DeletionMark=true → is_active=false."""
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, _products_payload())
    )
    # F003: активируем товар валидной ценой, иначе он уже неактивен
    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 350.0,
                "Актуальность": True,
            }
        ],
    )
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, prices_payload)
    )
    product = (
        await test_session.execute(
            select(Product).where(Product.onec_id == GUID_PRODUCT_1)
        )
    ).scalar_one()
    assert product.is_active is True

    deleted_payload = _odata(
        "Catalog_Номенклатура",
        [
            {
                "Ref_Key": GUID_PRODUCT_1,
                "Description": "Кабель ВВГнг 3х2,5",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": True,
            }
        ],
    )
    intake_id_2 = await _make_intake(test_session, fake_storage, deleted_payload)
    stats = await process_intake(test_session, intake_id_2)

    result = await test_session.execute(
        select(Product).where(Product.onec_id == GUID_PRODUCT_1)
    )
    product = result.scalar_one()
    assert product.is_active is False
    assert stats.products_deactivated == 1


# ─── OData: атрибуты ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_attribute_value_number_unit(
    test_session, fake_storage, patched_settings
):
    """AC: «Сечение 10,0мм2» → value_number=10.0, unit=мм² в справочнике."""
    defs_payload = _odata(
        "ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения",
        [
            {
                "Ref_Key": GUID_ATTR_SECTION,
                "Description": "Сечение",
                "DeletionMark": False,
                "ValueType": {"Types": ["String"]},
            }
        ],
    )
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, defs_payload)
    )
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, _products_payload())
    )
    values_payload = _odata(
        "Catalog_Номенклатура_ДополнительныеРеквизиты",
        [
            {
                "Ref_Key": GUID_PRODUCT_1,
                "Свойство_Key": GUID_ATTR_SECTION,
                "Значение": "10,0мм2",
                "Значение_Type": "String",
                "ТекстоваяСтрока": "10,0мм2",
            }
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, values_payload)
    )

    assert stats.values_upserted == 1
    attribute = (
        await test_session.execute(
            select(Attribute).where(Attribute.onec_id == GUID_ATTR_SECTION)
        )
    ).scalar_one()
    assert attribute.name == "Сечение"
    assert attribute.unit == "мм²"

    value = (
        await test_session.execute(
            select(ProductAttributeValue).where(
                ProductAttributeValue.attribute_id == attribute.id
            )
        )
    ).scalar_one()
    assert float(value.value_number) == 10.0
    assert value.value_text is None

    # Идемпотентность значений: повторный разбор не создаёт дублей
    stats2 = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, values_payload)
    )
    assert stats2.values_upserted == 1  # upsert той же строки
    count = (
        await test_session.execute(
            select(func.count()).select_from(ProductAttributeValue)
        )
    ).scalar_one()
    assert count == 1


# ─── OData: цены и остатки ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_prices_and_stock(
    test_session, fake_storage, patched_settings
):
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, _products_payload())
    )

    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 350.50,
                "Актуальность": True,
            },
            {  # другой вид цен — тоже пишется (отдельной строкой, D-08)
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": "99999999-9999-9999-9999-999999999999",
                "Цена": 100.0,
                "Актуальность": True,
            },
            {  # неактуальная цена — игнорируется
                "Номенклатура_Key": GUID_PRODUCT_2,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 200.0,
                "Актуальность": False,
            },
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, prices_payload)
    )
    assert stats.prices_applied == 2

    stock_payload = _odata(
        "AccumulationRegister_ЗапасыНаСкладах_Balance",
        [
            {"Номенклатура_Key": GUID_PRODUCT_1, "КоличествоBalance": 10},
            {"Номенклатура_Key": GUID_PRODUCT_1, "КоличествоBalance": 5},
            {"Номенклатура_Key": GUID_PRODUCT_2, "КоличествоBalance": -4},
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, stock_payload)
    )
    assert stats.stock_applied == 2

    product1 = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    product2 = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_2))
    ).scalar_one()
    # Два вида цен — две строки product_prices, не перезатираются (D-08)
    assert await _price_of(test_session, product1.id) == Decimal("350.50")
    assert await _price_of(
        test_session, product1.id, "99999999-9999-9999-9999-999999999999"
    ) == Decimal("100.00")
    assert product1.stock == 15  # сумма по складам
    assert product2.stock == 0  # отрицательный остаток клампится (B-02)


# ─── OData: категории ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_categories_with_parent(
    test_session, fake_storage, patched_settings
):
    parent_guid = "77777777-7777-7777-7777-777777777777"
    payload = _odata(
        "Catalog_КатегорииНоменклатуры",
        [
            # Ребёнок идёт раньше родителя — parent_id выставляется вторым проходом
            {"Ref_Key": GUID_CATEGORY, "Description": "Кабели ВВГ", "Parent_Key": parent_guid},
            {
                "Ref_Key": parent_guid,
                "Description": "Кабели",
                "Parent_Key": "00000000-0000-0000-0000-000000000000",
            },
        ],
    )
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, payload)
    )

    child = (
        await test_session.execute(select(Category).where(Category.onec_id == GUID_CATEGORY))
    ).scalar_one()
    parent = (
        await test_session.execute(select(Category).where(Category.onec_id == parent_guid))
    ).scalar_one()
    assert child.parent_id == parent.id
    assert parent.parent_id is None  # нулевой GUID = NULL


@pytest.mark.asyncio
async def test_loader_category_adopts_seeded_category_by_name(
    test_session, fake_storage, patched_settings
):
    """Дедупликация: seed-категория (onec_id IS NULL) с тем же именем усваивается
    — дубль не создаётся, onec_id проставляется, parent резолвится вторым проходом."""
    parent_guid = "88888888-8888-8888-8888-888888888888"
    seeded = Category(name="Розетки", onec_id=None, is_active=True)
    test_session.add(seeded)
    await test_session.commit()

    payload = _odata(
        "Catalog_КатегорииНоменклатуры",
        [
            # Ребёнок раньше родителя — parent_id выставляется вторым проходом
            {"Ref_Key": GUID_CATEGORY, "Description": "Розетки", "Parent_Key": parent_guid},
            {
                "Ref_Key": parent_guid,
                "Description": "Электрика",
                "Parent_Key": "00000000-0000-0000-0000-000000000000",
            },
        ],
    )
    intake_id = await _make_intake(test_session, fake_storage, payload)
    stats = await process_intake(test_session, intake_id)

    assert stats.categories_created == 1  # только «Электрика»
    assert stats.categories_updated == 1  # усвоенная «Розетки»

    namesakes = (
        await test_session.execute(select(Category).where(Category.name == "Розетки"))
    ).scalars().all()
    assert len(namesakes) == 1  # дубль не создан
    adopted = namesakes[0]
    assert adopted.id == seeded.id
    assert adopted.onec_id == GUID_CATEGORY
    assert adopted.is_active is True
    assert adopted.onec_sync_at is not None

    parent = (
        await test_session.execute(select(Category).where(Category.onec_id == parent_guid))
    ).scalar_one()
    assert adopted.parent_id == parent.id

    # Идемпотентность: повторный разбор не создаёт новых категорий
    stats2 = await process_intake(test_session, intake_id)
    assert stats2.categories_created == 0
    count = (
        await test_session.execute(
            select(func.count()).select_from(Category).where(Category.name == "Розетки")
        )
    ).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_loader_category_with_other_onec_id_not_adopted(
    test_session, fake_storage, patched_settings
):
    """Категория с тем же именем, но другим onec_id (уже из 1С) НЕ усваивается —
    защита от слияния разных 1С-групп. Characterization-тест: поведение не менялось."""
    other_guid = "99999999-9999-9999-9999-999999999999"
    existing = Category(name="Розетки", onec_id=other_guid, is_active=True)
    test_session.add(existing)
    await test_session.commit()

    payload = _odata(
        "Catalog_КатегорииНоменклатуры",
        [{"Ref_Key": GUID_CATEGORY, "Description": "Розетки"}],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, payload)
    )

    assert stats.categories_created == 1
    await test_session.refresh(existing)
    assert existing.onec_id == other_guid  # владелец onec_id не пострадал

    namesakes = (
        await test_session.execute(select(Category).where(Category.name == "Розетки"))
    ).scalars().all()
    assert len(namesakes) == 2
    assert {c.onec_id for c in namesakes} == {other_guid, GUID_CATEGORY}


# ─── CommerceML (диалект мока, FORMAT_MAP.md §6) ─────────────────────────────


IMPORT_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.10">
  <Классификатор>
    <Ид>classifier-1</Ид>
    <Наименование>Классификатор (Каталог товаров)</Наименование>
    <Группы>
      <Группа><Ид>{GUID_CATEGORY}</Ид><Наименование>Кабели</Наименование></Группа>
    </Группы>
    <Свойства>
      <Свойство><Ид>{GUID_ATTR_SECTION}</Ид><Наименование>Сечение</Наименование><ТипЗначений>Строка</ТипЗначений></Свойство>
    </Свойства>
  </Классификатор>
  <Каталог СодержитТолькоИзменения="true">
    <Ид>catalog-1</Ид>
    <Товары>
      <Товар>
        <Ид>{GUID_PRODUCT_1}</Ид>
        <Артикул>KB-001</Артикул>
        <Наименование>Кабель ВВГнг 3х2,5</Наименование>
        <Группы><Ид>{GUID_CATEGORY}</Ид></Группы>
        <Описание>Кабель силовой</Описание>
        <ЗначенияСвойств>
          <ЗначенияСвойства><Ид>{GUID_ATTR_SECTION}</Ид><Значение>2,5</Значение></ЗначенияСвойства>
        </ЗначенияСвойств>
      </Товар>
      <Товар>
        <Ид>{GUID_PRODUCT_DEL}</Ид>
        <Наименование>Удалённый товар</Наименование>
        <ПометкаУдаления>true</ПометкаУдаления>
      </Товар>
    </Товары>
  </Каталог>
</КоммерческаяИнформация>
"""

OFFERS_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.10">
  <ПакетПредложений СодержитТолькоИзменения="true">
    <Ид>offers-1</Ид>
    <Предложения>
      <Предложение>
        <Ид>{GUID_PRODUCT_1}</Ид>
        <Артикул>KB-001</Артикул>
        <Наименование>Кабель ВВГнг 3х2,5</Наименование>
        <Цены><Цена><ЦенаЗаЕдиницу>350.00</ЦенаЗаЕдиницу></Цена></Цены>
        <Количество>42</Количество>
      </Предложение>
    </Предложения>
  </ПакетПредложений>
</КоммерческаяИнформация>
"""


@pytest.mark.asyncio
async def test_loader_commerceml_zip(test_session, fake_storage, patched_settings):
    # Предсоздаём товар, который придёт с ПометкаУдаления
    await make_product(
        test_session,
        onec_id=GUID_PRODUCT_DEL,
        name="Удалённый товар",
        price=10,
        stock=1,
        supplier_id=patched_settings.onec_default_supplier_id,
        is_active=True,
    )
    await test_session.commit()

    payload = _cml_zip(IMPORT_XML, OFFERS_XML)
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, payload)
    )

    assert stats.products_created == 1
    assert stats.products_deactivated == 1
    assert stats.prices_applied == 1
    assert stats.stock_applied == 1
    assert stats.values_upserted == 1

    product = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    assert product.sku == "KB-001"
    # Цена из CML без ИдТипаЦены пишется сайтовым видом (fallback, D-08)
    assert await _price_of(test_session, product.id) == Decimal("350.00")
    assert product.stock == 42
    assert product.is_active is True

    category = (
        await test_session.execute(select(Category).where(Category.onec_id == GUID_CATEGORY))
    ).scalar_one()
    assert product.category_id == category.id

    attribute = (
        await test_session.execute(
            select(Attribute).where(Attribute.onec_id == GUID_ATTR_SECTION)
        )
    ).scalar_one()
    value = (
        await test_session.execute(
            select(ProductAttributeValue).where(
                ProductAttributeValue.attribute_id == attribute.id
            )
        )
    ).scalar_one()
    assert float(value.value_number) == 2.5

    deleted = (
        await test_session.execute(
            select(Product).where(Product.onec_id == GUID_PRODUCT_DEL)
        )
    ).scalar_one()
    assert deleted.is_active is False


# ─── Ошибки и job SEARCH_INDEX_PRODUCTS ───────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_broken_payload_marks_failed(
    test_session, fake_storage, patched_settings
):
    intake_id = await _make_intake(test_session, fake_storage, b"{broken json")

    with pytest.raises(ValueError, match="No parseable documents"):
        await process_intake(test_session, intake_id)

    log_id = (
        await test_session.execute(
            select(OnecIntakeLog.id).where(OnecIntakeLog.intake_id == intake_id)
        )
    ).scalar_one()
    log = await test_session.get(OnecIntakeLog, log_id)
    assert log.status == "failed"
    assert log.error


@pytest.mark.asyncio
async def test_loader_missing_object_marks_failed(
    test_session, fake_storage, patched_settings
):
    # intake-запись есть, а объекта в хранилище нет
    log = OnecIntakeLog(
        bucket="onec-intake",
        object_key="missing/object.bin",
        content_type="application/octet-stream",
        received_bytes=1,
        sha256="0" * 64,
        status="received",
    )
    test_session.add(log)
    await test_session.commit()

    with pytest.raises(FileNotFoundError):
        await process_intake(test_session, str(log.intake_id))

    fresh = await test_session.get(OnecIntakeLog, log.id)
    assert fresh.status == "failed"


@pytest.mark.asyncio
async def test_loader_enqueues_search_index_job(
    test_session, fake_storage, patched_settings
):
    intake_id = await _make_intake(test_session, fake_storage, _products_payload())
    await process_intake(test_session, intake_id)

    result = await test_session.execute(
        select(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
    )
    jobs = result.scalars().all()
    assert len(jobs) == 1
    product_ids = jobs[0].payload["product_ids"]
    expected = (
        (await test_session.execute(select(Product.id))).scalars().all()
    )
    assert sorted(product_ids) == sorted(expected)


# ─── F002: дубли sku не роняют импорт ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_duplicate_skus_does_not_poison_file(
    test_session, fake_storage, patched_settings
):
    """F002: два товара с одинаковым Артикул — файл разбирается (parsed),
    второй товар остаётся без sku, конфликт фиксируется в stats.errors."""
    payload = _odata(
        "Catalog_Номенклатура",
        [
            {
                "Ref_Key": GUID_PRODUCT_1,
                "Description": "Первый",
                "Артикул": "DUP-001",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
            },
            {
                "Ref_Key": GUID_PRODUCT_2,
                "Description": "Второй",
                "Артикул": "DUP-001",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
            },
        ],
    )
    intake_id = await _make_intake(test_session, fake_storage, payload)
    stats = await process_intake(test_session, intake_id)

    assert stats.products_created == 2
    assert any("duplicate sku" in e for e in stats.errors)

    product1 = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    product2 = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_2))
    ).scalar_one()
    assert product1.sku == "DUP-001"
    assert product2.sku is None

    log_id = (
        await test_session.execute(
            select(OnecIntakeLog.id).where(OnecIntakeLog.intake_id == intake_id)
        )
    ).scalar_one()
    log = await test_session.get(OnecIntakeLog, log_id)
    assert log.status == "parsed"


# ─── F003: правило «цена > 0» (B-01) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_price_activates_product(
    test_session, fake_storage, patched_settings
):
    """F003: новый товар неактивен до первой валидной цены > 0."""
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, _products_payload())
    )
    product = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    assert product.is_active is False

    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 350.0,
                "Актуальность": True,
            }
        ],
    )
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, prices_payload)
    )
    await test_session.refresh(product)
    assert product.is_active is True
    assert await _price_of(test_session, product.id) == Decimal("350.00")


@pytest.mark.asyncio
async def test_loader_non_positive_price_ignored(
    test_session, fake_storage, patched_settings
):
    """F003: цена 0/отрицательная не перезаписывает валидную (B-01)."""
    existing = await make_product(
        test_session,
        onec_id=GUID_PRODUCT_1,
        name="Товар с ценой",
        price=500,
        price_type=GUID_PRICE_TYPE,
        stock=1,
        supplier_id=patched_settings.onec_default_supplier_id,
        is_active=True,
    )
    await test_session.commit()

    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 0,
                "Актуальность": True,
            },
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": -10,
                "Актуальность": True,
            },
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, prices_payload)
    )

    assert stats.prices_applied == 0
    assert len([e for e in stats.errors if "non-positive price" in e]) == 2
    await test_session.refresh(existing)
    assert await _price_of(test_session, existing.id) == Decimal("500.00")
    assert existing.is_active is True


# ─── F004: лимит распаковки ZIP (zip-bomb) ────────────────────────────────────


@pytest.mark.asyncio
async def test_loader_zip_bomb_rejected(
    test_session, fake_storage, patched_settings, monkeypatch
):
    """F004: суммарный размер распакованных данных ограничен — файл в failed."""
    monkeypatch.setattr(
        "src.app.services.onec_intake_loader.ZIP_MAX_EXTRACTED_BYTES", 1024
    )
    big_xml = "<x>" + "A" * 4096 + "</x>"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("big.xml", big_xml)
    intake_id = await _make_intake(test_session, fake_storage, buffer.getvalue())

    with pytest.raises(ValueError, match="zip-bomb"):
        await process_intake(test_session, intake_id)

    log_id = (
        await test_session.execute(
            select(OnecIntakeLog.id).where(OnecIntakeLog.intake_id == intake_id)
        )
    ).scalar_one()
    log = await test_session.get(OnecIntakeLog, log_id)
    assert log.status == "failed"


# ─── F007: reparse без изменений не ставит SEARCH_INDEX_PRODUCTS ──────────────


@pytest.mark.asyncio
async def test_loader_reparse_without_changes_skips_index_job(
    test_session, fake_storage, patched_settings
):
    """F007: идемпотентный повторный разбор не создаёт лишний job переиндексации."""
    payload = _products_payload()
    intake_id = await _make_intake(test_session, fake_storage, payload)
    await process_intake(test_session, intake_id)
    jobs_after_first = (
        await test_session.execute(
            select(func.count()).select_from(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
    ).scalar_one()
    assert jobs_after_first == 1

    stats = await process_intake(test_session, intake_id)
    jobs_after_second = (
        await test_session.execute(
            select(func.count()).select_from(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
    ).scalar_one()
    assert stats.products_created == 0
    assert jobs_after_second == 1  # изменений не было — новый job не поставлен


@pytest.mark.asyncio
async def test_loader_prices_reparse_without_changes_skips_index_job(
    test_session, fake_storage, patched_settings
):
    """F001/F007: повторный разбор того же prices-файла без изменений —
    новый job SEARCH_INDEX_PRODUCTS не ставится (обновление onec_sync_at
    само по себе изменением не считается)."""
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, _products_payload())
    )
    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 350.0,
                "Актуальность": True,
            }
        ],
    )
    prices_intake_id = await _make_intake(test_session, fake_storage, prices_payload)
    # Первый разбор: цена создана + товар активирован → touched, job поставлен
    await process_intake(test_session, prices_intake_id)
    jobs_after_first = (
        await test_session.execute(
            select(func.count()).select_from(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
    ).scalar_one()

    # Reparse того же файла: цена не изменилась — товар не попадает в touched
    await process_intake(test_session, prices_intake_id)
    jobs_after_second = (
        await test_session.execute(
            select(func.count()).select_from(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
    ).scalar_one()
    assert jobs_after_second == jobs_after_first


# ─── F008: O(1) sku-индекс (конфликт по данным БД, не только in-run) ──────────


@pytest.mark.asyncio
async def test_loader_sku_conflict_with_db_product(
    test_session, fake_storage, patched_settings
):
    """F008: sku занят товаром из БД (другой onec_id, не из текущего файла) —
    новому товару sku не присваивается, файл parsed."""
    existing = await make_product(
        test_session,
        onec_id=GUID_PRODUCT_DEL,
        name="Существующий",
        sku="TAKEN-001",
        price=100,
        stock=1,
        supplier_id=patched_settings.onec_default_supplier_id,
        is_active=True,
    )
    await test_session.commit()

    payload = _odata(
        "Catalog_Номенклатура",
        [
            {
                "Ref_Key": GUID_PRODUCT_1,
                "Description": "Новый с чужим артикулом",
                "Артикул": "TAKEN-001",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
            }
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, payload)
    )

    assert stats.products_created == 1
    assert any("duplicate sku" in e for e in stats.errors)
    product = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    assert product.sku is None
    await test_session.refresh(existing)
    assert existing.sku == "TAKEN-001"  # владелец sku не пострадал


@pytest.mark.asyncio
async def test_loader_sku_reassign_updates_index(
    test_session, fake_storage, patched_settings
):
    """F008: переназначение sku освобождает старый ключ индекса — другой товар
    может занять освободившийся sku в том же прогоне."""
    payload = _odata(
        "Catalog_Номенклатура",
        [
            {
                "Ref_Key": GUID_PRODUCT_1,
                "Description": "Первый",
                "Артикул": "OLD-001",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
            },
            {
                # Тот же товар со сменой артикула
                "Ref_Key": GUID_PRODUCT_1,
                "Description": "Первый",
                "Артикул": "NEW-001",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
            },
            {
                "Ref_Key": GUID_PRODUCT_2,
                "Description": "Второй",
                "Артикул": "OLD-001",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": False,
            },
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, payload)
    )

    assert not [e for e in stats.errors if "duplicate sku" in e]
    product1 = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    product2 = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_2))
    ).scalar_one()
    assert product1.sku == "NEW-001"
    assert product2.sku == "OLD-001"


# ─── F009: цена не реанимирует soft-deleted товар из прошлого прогона ─────────


@pytest.mark.asyncio
async def test_loader_price_does_not_revive_soft_deleted_product(
    test_session, fake_storage, patched_settings
):
    """F009: DeletionMark-файл → prices-файл → is_active остаётся False,
    цена при этом обновляется."""
    existing = await make_product(
        test_session,
        onec_id=GUID_PRODUCT_1,
        name="Товар",
        sku="KB-001",
        price=300,
        price_type=GUID_PRICE_TYPE,
        stock=5,
        supplier_id=patched_settings.onec_default_supplier_id,
        is_active=True,
    )
    await test_session.commit()

    # 1. Файл с DeletionMark=true → soft-delete
    deleted_payload = _odata(
        "Catalog_Номенклатура",
        [
            {
                "Ref_Key": GUID_PRODUCT_1,
                "Description": "Товар",
                "ТипНоменклатуры": "Запас",
                "IsFolder": False,
                "DeletionMark": True,
            }
        ],
    )
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, deleted_payload)
    )
    await test_session.refresh(existing)
    assert existing.is_active is False

    # 2. Отдельный файл цен (другой прогон, cache.deleted пуст) — НЕ реанимирует
    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 350.0,
                "Актуальность": True,
            }
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, prices_payload)
    )

    assert stats.prices_applied == 1
    await test_session.refresh(existing)
    assert await _price_of(test_session, existing.id) == Decimal("350.00")  # цена обновилась
    assert existing.is_active is False  # но товар не воскрес


# ─── Handler ONEC_INTAKE_PROCESS в job_worker ─────────────────────────────────


def test_worker_handler_registered():
    from src.app.workers.job_worker import HANDLERS

    assert "ONEC_INTAKE_PROCESS" in HANDLERS


@pytest.mark.asyncio
async def test_worker_handler_requires_intake_id(test_session):
    from src.app.workers.job_worker import handle_onec_intake_process_job

    job = Job(job_type="ONEC_INTAKE_PROCESS", payload={})
    with pytest.raises(ValueError, match="missing intake_id"):
        await handle_onec_intake_process_job(job, test_session)


@pytest.mark.asyncio
async def test_worker_handler_appends_stats_to_processing_log(
    test_session, fake_storage, patched_settings
):
    from src.app.workers.job_worker import handle_onec_intake_process_job

    intake_id = await _make_intake(test_session, fake_storage, _products_payload())
    job = Job(job_type="ONEC_INTAKE_PROCESS", payload={"intake_id": intake_id})
    test_session.add(job)
    await test_session.commit()

    await handle_onec_intake_process_job(job, test_session)

    assert job.processing_log
    assert "products +2" in job.processing_log[-1]


# ─── D-08: все виды цен пишутся, активация — только сайтовой ──────────────────

GUID_PRICE_TYPE_COST = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_loader_odata_multiple_price_types_stored(
    test_session, fake_storage, patched_settings
):
    """AC: OData с двумя ВидЦен_Key → две строки product_prices, не перезатираются."""
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, _products_payload())
    )
    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE,
                "Цена": 350.0,
                "Актуальность": True,
            },
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE_COST,
                "Цена": 120.0,
                "Актуальность": True,
            },
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, prices_payload)
    )

    assert stats.prices_applied == 2
    product = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    assert await _price_of(test_session, product.id) == Decimal("350.00")
    assert await _price_of(test_session, product.id, GUID_PRICE_TYPE_COST) == Decimal("120.00")


@pytest.mark.asyncio
async def test_loader_non_site_price_does_not_activate(
    test_session, fake_storage, patched_settings
):
    """AC: несайтовый вид цены (себестоимость) товар НЕ активирует (F003)."""
    await process_intake(
        test_session, await _make_intake(test_session, fake_storage, _products_payload())
    )
    prices_payload = _odata(
        "InformationRegister_ЦеныНоменклатуры",
        [
            {
                "Номенклатура_Key": GUID_PRODUCT_1,
                "ВидЦен_Key": GUID_PRICE_TYPE_COST,
                "Цена": 120.0,
                "Актуальность": True,
            }
        ],
    )
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, prices_payload)
    )

    assert stats.prices_applied == 1
    product = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    assert product.is_active is False  # сайтовой цены не было — товар скрыт
    assert await _price_of(test_session, product.id) is None
    assert await _price_of(test_session, product.id, GUID_PRICE_TYPE_COST) == Decimal("120.00")


OFFERS_XML_TWO_PRICE_TYPES = f"""<?xml version="1.0" encoding="UTF-8"?>
<КоммерческаяИнформация ВерсияСхемы="2.10">
  <ПакетПредложений СодержитТолькоИзменения="true">
    <Ид>offers-2</Ид>
    <Предложения>
      <Предложение>
        <Ид>{GUID_PRODUCT_1}</Ид>
        <Наименование>Кабель ВВГнг 3х2,5</Наименование>
        <Цены>
          <Цена>
            <ИдТипаЦены>{GUID_PRICE_TYPE}</ИдТипаЦены>
            <ЦенаЗаЕдиницу>350.00</ЦенаЗаЕдиницу>
          </Цена>
          <Цена>
            <ИдТипаЦены>{GUID_PRICE_TYPE_COST}</ИдТипаЦены>
            <ЦенаЗаЕдиницу>120.00</ЦенаЗаЕдиницу>
          </Цена>
        </Цены>
        <Количество>42</Количество>
      </Предложение>
    </Предложения>
  </ПакетПредложений>
</КоммерческаяИнформация>
"""


@pytest.mark.asyncio
async def test_loader_cml_offers_multiple_price_types_stored(
    test_session, fake_storage, patched_settings
):
    """AC: CML offers с двумя Цена (разные ИдТипаЦены) → две строки product_prices."""
    payload = _cml_zip(IMPORT_XML, OFFERS_XML_TWO_PRICE_TYPES)
    stats = await process_intake(
        test_session, await _make_intake(test_session, fake_storage, payload)
    )

    assert stats.prices_applied == 2
    product = (
        await test_session.execute(select(Product).where(Product.onec_id == GUID_PRODUCT_1))
    ).scalar_one()
    assert await _price_of(test_session, product.id) == Decimal("350.00")
    assert await _price_of(test_session, product.id, GUID_PRICE_TYPE_COST) == Decimal("120.00")
    # Активация — сайтовой ценой из того же offers-файла
    assert product.is_active is True
