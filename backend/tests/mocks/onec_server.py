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
        "Parent_Key": None,
        "Description": "Electronics",
    },
    {
        "Ref_Key": "22222222-2222-2222-2222-222222222222",
        "Parent_Key": "11111111-1111-1111-1111-111111111111",
        "Description": "Phones",
    },
]

PRODUCTS = [
    {
        "Ref_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "Description": "Smartphone X",
        "Артикул": "PHONE-001",
        "Code": "000000001",
        "Parent_Key": "22222222-2222-2222-2222-222222222222",
        "IsFolder": False,
        "ТипНоменклатуры": "Запас",
    },
    {
        "Ref_Key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "Description": "Folder Group",
        "Артикул": None,
        "Code": "000000002",
        "Parent_Key": None,
        "IsFolder": True,
        "ТипНоменклатуры": "Запас",
    },
    {
        "Ref_Key": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "Description": "Service Item",
        "Артикул": "SRV-003",
        "Code": "000000003",
        "Parent_Key": None,
        "IsFolder": False,
        "ТипНоменклатуры": "Услуга",
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
        "Склад_Key": "99999999-9999-9999-9999-999999999999",
        "КоличествоBalance": 12.0,
    },
    {
        "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "Склад_Key": "00000000-0000-0000-0000-000000000001",
        "КоличествоBalance": 8.0,
    },
    {
        "Номенклатура_Key": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "Склад_Key": "99999999-9999-9999-9999-999999999999",
        "КоличествоBalance": 3.0,
    },
]


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
            if stock["Склад_Key"] in filter_expr:
                items = [s for s in items if s["Склад_Key"] == stock["Склад_Key"]]
                break
    return {"value": _paginate(items, top, skip)}
