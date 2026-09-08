"""Mock OData server for 1C:УНФ used in pytest."""

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()

MOCK_LOGIN = "test-user"
MOCK_PASSWORD = "test-pass"

# ─── Sample fixtures ─────────────────────────────────────────────────────────

CATEGORIES = [
    {
        "Ref_Key": "11111111-1111-1111-1111-111111111111",
        "Parent_Key": "00000000-0000-0000-0000-000000000000",
        "Description": "Electronics",
        "DeletionMark": False,
    },
    {
        "Ref_Key": "22222222-2222-2222-2222-222222222222",
        "Parent_Key": "11111111-1111-1111-1111-111111111111",
        "Description": "Phones",
        "DeletionMark": False,
    },
]

PRODUCTS = [
    {
        "Ref_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "Description": "Smartphone X",
        "НаименованиеПолное": "Smartphone X 256GB Black",
        "Артикул": "PHONE-001",
        "Code": "000000001",
        "Parent_Key": "00000000-0000-0000-0000-000000000000",
        "КатегорияНоменклатуры_Key": "22222222-2222-2222-2222-222222222222",
        "IsFolder": False,
        "ТипНоменклатуры": "Запас",
        "Вес": 0.25,
        "DeletionMark": False,
    },
    {
        "Ref_Key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "Description": "Folder Group",
        "НаименованиеПолное": "Folder Group",
        "Артикул": None,
        "Code": "000000002",
        "Parent_Key": "00000000-0000-0000-0000-000000000000",
        "КатегорияНоменклатуры_Key": "00000000-0000-0000-0000-000000000000",
        "IsFolder": True,
        "ТипНоменклатуры": "Запас",
        "Вес": 0,
        "DeletionMark": False,
    },
    {
        "Ref_Key": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "Description": "Service Item",
        "НаименованиеПолное": "",
        "Артикул": "SRV-003",
        "Code": "000000003",
        "Parent_Key": "00000000-0000-0000-0000-000000000000",
        "КатегорияНоменклатуры_Key": "00000000-0000-0000-0000-000000000000",
        "IsFolder": False,
        "ТипНоменклатуры": "Услуга",
        "Вес": 0,
        "DeletionMark": True,
    },
]

PRICES = [
    {
        "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "ВидЦен_Key": "77777777-7777-7777-7777-777777777777",
        "Цена": 999.99,
    },
    {
        "Номенклатура_Key": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "ВидЦен_Key": "77777777-7777-7777-7777-777777777777",
        "Цена": 499.50,
    },
    {
        "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "ВидЦен_Key": "88888888-8888-8888-8888-888888888888",
        "Цена": 1099.99,
    },
]

STOCKS = [
    {
        "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "СтруктурнаяЕдиница_Key": "99999999-9999-9999-9999-999999999999",
        "КоличествоBalance": 12.0,
    },
    {
        "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "СтруктурнаяЕдиница_Key": "00000000-0000-0000-0000-000000000001",
        "КоличествоBalance": 8.0,
    },
    {
        "Номенклатура_Key": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "СтруктурнаяЕдиница_Key": "99999999-9999-9999-9999-999999999999",
        "КоличествоBalance": 3.0,
    },
]

ATTRIBUTE_DEFINITIONS = [
    {
        "Ref_Key": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "Description": "Цвет",
        "Заголовок": "Цвет корпуса",
        "DeletionMark": False,
        "ValueType": {"Types": ["CatalogRef.ЗначенияСвойствОбъектов"]},
    },
    {
        "Ref_Key": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "Description": "Мощность",
        "Заголовок": "",
        "DeletionMark": False,
        "ValueType": {"Types": ["Number"]},
    },
]

ATTRIBUTE_VALUES = [
    {
        "Ref_Key": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "Description": "Чёрный",
        "Owner_Key": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "DeletionMark": False,
    },
    {
        "Ref_Key": "12121212-1212-1212-1212-121212121212",
        "Description": "Белый",
        "Owner_Key": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "DeletionMark": False,
    },
]

PRODUCT_ATTRIBUTES = [
    {
        "Ref_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "LineNumber": "1",
        "Свойство_Key": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "Значение": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "Значение_Type": "StandardODATA.Catalog_ЗначенияСвойствОбъектов",
        "ТекстоваяСтрока": "",
    },
    {
        "Ref_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "LineNumber": "2",
        "Свойство_Key": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "Значение": "00000000-0000-0000-0000-000000000000",
        "Значение_Type": "Edm.String",
        "ТекстоваяСтрока": "65 Вт",
    },
    # Строка для товара вне выгруженного подмножества — sync должен пропустить
    {
        "Ref_Key": "99999999-8888-7777-6666-555555555555",
        "LineNumber": "1",
        "Свойство_Key": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "Значение": "ffffffff-ffff-ffff-ffff-ffffffffffff",
        "Значение_Type": "StandardODATA.Catalog_ЗначенияСвойствОбъектов",
        "ТекстоваяСтрока": "",
    },
]

PRODUCT_FILES = [
    {
        "Ref_Key": "34343434-3434-3434-3434-343434343434",
        "Description": "b_front",
        "ВладелецФайла_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "Размер": "123807",
        "Расширение": "jpg",
        "DeletionMark": False,
    },
    {
        "Ref_Key": "45454545-4545-4545-4545-454545454545",
        "Description": "a_box",
        "ВладелецФайла_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "Размер": "5678",
        "Расширение": "png",
        "DeletionMark": False,
    },
    {
        "Ref_Key": "56565656-5656-5656-5656-565656565656",
        "Description": "deleted",
        "ВладелецФайла_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "Размер": "100",
        "Расширение": "jpg",
        "DeletionMark": True,
    },
]

FILE_BINARY = b"\xff\xd8\xff\xe0" + b"fake-jpeg" * 16 + b"\xff\xd9"


# ─── Auth ────────────────────────────────────────────────────────────────────


def _verify_basic(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    if credentials.username != MOCK_LOGIN or credentials.password != MOCK_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")


# ─── Pagination helpers ──────────────────────────────────────────────────────


def _paginate(items: list[dict[str, Any]], top: int, skip: int) -> list[dict[str, Any]]:
    return items[skip : skip + top]


# ─── Endpoints ───────────────────────────────────────────────────────────────


@app.get("/Catalog_КатегорииНоменклатуры")
async def get_categories(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    _auth: None = Depends(_verify_basic),
):
    return {"value": _paginate(CATEGORIES, top, skip)}


@app.get("/Catalog_Номенклатура")
async def get_products(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    filter_expr: str | None = Query(None, alias="$filter"),
    _auth: None = Depends(_verify_basic),
):
    items = PRODUCTS
    if filter_expr:
        # Minimal OData filter support used by OnecClient.
        if "IsFolder eq false" in filter_expr:
            items = [p for p in items if not p["IsFolder"]]
        if "ТипНоменклатуры eq 'Запас'" in filter_expr:
            items = [p for p in items if p["ТипНоменклатуры"] == "Запас"]
    return {"value": _paginate(items, top, skip)}


@app.get("/InformationRegister_ЦеныНоменклатуры")
async def get_prices(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    filter_expr: str | None = Query(None, alias="$filter"),
    _auth: None = Depends(_verify_basic),
):
    items = PRICES
    if filter_expr:
        # Extract GUID from expression like "ВидЦен_Key eq 77777777-..."
        for price in PRICES:
            if price["ВидЦен_Key"] in filter_expr:
                items = [p for p in items if p["ВидЦен_Key"] == price["ВидЦен_Key"]]
                break
    return {"value": _paginate(items, top, skip)}


@app.get("/AccumulationRegister_ЗапасыНаСкладах/Balance")
async def get_stock_balance(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    filter_expr: str | None = Query(None, alias="$filter"),
    _auth: None = Depends(_verify_basic),
):
    items = STOCKS
    if filter_expr:
        for stock in STOCKS:
            if stock["СтруктурнаяЕдиница_Key"] in filter_expr:
                items = [
                    s
                    for s in items
                    if s["СтруктурнаяЕдиница_Key"] == stock["СтруктурнаяЕдиница_Key"]
                ]
                break
    return {"value": _paginate(items, top, skip)}


@app.get("/ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения")
async def get_attribute_definitions(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    _auth: None = Depends(_verify_basic),
):
    return {"value": _paginate(ATTRIBUTE_DEFINITIONS, top, skip)}


@app.get("/Catalog_ЗначенияСвойствОбъектов")
async def get_attribute_values(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    filter_expr: str | None = Query(None, alias="$filter"),
    _auth: None = Depends(_verify_basic),
):
    items = ATTRIBUTE_VALUES
    if filter_expr:
        for value in ATTRIBUTE_VALUES:
            if value["Owner_Key"] in filter_expr:
                items = [v for v in items if v["Owner_Key"] == value["Owner_Key"]]
                break
    return {"value": _paginate(items, top, skip)}


@app.get("/Catalog_Номенклатура_ДополнительныеРеквизиты")
async def get_product_attributes(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    filter_expr: str | None = Query(None, alias="$filter"),
    _auth: None = Depends(_verify_basic),
):
    items = PRODUCT_ATTRIBUTES
    if filter_expr:
        for row in PRODUCT_ATTRIBUTES:
            if row["Ref_Key"] in filter_expr:
                items = [r for r in items if r["Ref_Key"] == row["Ref_Key"]]
                break
    return {"value": _paginate(items, top, skip)}


@app.get("/Catalog_НоменклатураПрисоединенныеФайлы")
async def get_product_files(
    top: int = Query(100, ge=0, alias="$top"),
    skip: int = Query(0, ge=0, alias="$skip"),
    filter_expr: str | None = Query(None, alias="$filter"),
    _auth: None = Depends(_verify_basic),
):
    items = PRODUCT_FILES
    if filter_expr:
        for file in PRODUCT_FILES:
            if file["ВладелецФайла_Key"] in filter_expr:
                items = [f for f in items if f["ВладелецФайла_Key"] == file["ВладелецФайла_Key"]]
                break
    return {"value": _paginate(items, top, skip)}


@app.get("/Catalog_НоменклатураПрисоединенныеФайлы(guid'{ref_key}')/$value")
async def get_file_binary(ref_key: str, _auth: None = Depends(_verify_basic)):
    from fastapi import Response

    known = {f["Ref_Key"] for f in PRODUCT_FILES}
    if ref_key not in known:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=FILE_BINARY, media_type="image/jpeg")
