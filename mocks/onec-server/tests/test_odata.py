"""Тесты OData-контракта мока (issue #227): envelope, $filter, пагинация, ошибки, $value."""

import io

from PIL import Image

from conftest import (
    ATTR1,
    ATTR2,
    AUTH,
    CAT1,
    F1,
    P1,
    P2,
    P3_FOLDER,
    P4_SERVICE,
    PT_OPT,
    PT_RETAIL,
    VAL1,
    WH1,
)

BASE = "/odata/standard.odata"
NULL_GUID = "00000000-0000-0000-0000-000000000000"


async def get(client, path: str, **kwargs):
    return await client.get(f"{BASE}/{path}", auth=AUTH, **kwargs)


# ─── Auth ───────────────────────────────────────────────────────────────────


async def test_no_auth_returns_401_odata_error(client):
    response = await client.get(f"{BASE}/Catalog_Номенклатура")
    assert response.status_code == 401
    body = response.json()
    assert "odata.error" in body
    assert "message" in body["odata.error"]


async def test_wrong_password_returns_401(client):
    response = await client.get(f"{BASE}/Catalog_Номенклатура", auth=(AUTH[0], "wrong"))
    assert response.status_code == 401


# ─── Management API (без auth) ─────────────────────────────────────────────


async def test_health(client):
    response = await client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_status_counts(client):
    response = await client.get("/status/")
    assert response.status_code == 200
    body = response.json()
    assert body["tables"]["products"] == 4
    assert body["tables"]["categories"] == 2
    assert body["tables"]["prices"] == 3


# ─── Envelope и неизвестная сущность ────────────────────────────────────────


async def test_envelope_shape(client):
    response = await get(client, "Catalog_КатегорииНоменклатуры")
    assert response.status_code == 200
    body = response.json()
    assert (
        body["odata.metadata"]
        == "http://onec-mock:8100/odata/standard.odata/$metadata#Catalog_КатегорииНоменклатуры"
    )
    assert isinstance(body["value"], list)


async def test_unknown_entity_404_odata_error(client):
    response = await get(client, "AccumulationRegister_ТоварыНаСкладах")
    assert response.status_code == 404
    assert response.json() == {
        "odata.error": {
            "code": "8",
            "message": {
                "lang": "ru",
                "value": "Сущность 'AccumulationRegister_ТоварыНаСкладах' не найдена",
            },
        }
    }


# ─── Сущности ───────────────────────────────────────────────────────────────


async def test_categories_fields(client):
    body = (await get(client, "Catalog_КатегорииНоменклатуры")).json()
    by_key = {row["Ref_Key"]: row for row in body["value"]}
    assert by_key[CAT1] == {
        "Ref_Key": CAT1,
        "Description": "Кабель",
        "Parent_Key": NULL_GUID,
        "IsFolder": False,
        "DeletionMark": False,
    }
    assert by_key[CAT1.replace("1", "2")]["DeletionMark"] is True


async def test_products_fields(client):
    body = (await get(client, "Catalog_Номенклатура")).json()
    by_key = {row["Ref_Key"]: row for row in body["value"]}
    assert set(by_key) == {P1, P2, P3_FOLDER, P4_SERVICE}
    p1 = by_key[P1]
    assert p1["Description"] == "Кабель ВВГ 2х1.5"
    assert p1["НаименованиеПолное"] == "Кабель ВВГ 2х1.5 полное"
    assert p1["Артикул"] == "25-211"
    assert p1["Code"] == "НФ-00000001"
    assert p1["Parent_Key"] == NULL_GUID  # пустая строка → нулевой GUID
    assert p1["IsFolder"] is False
    assert p1["ТипНоменклатуры"] == "Запас"
    assert p1["КатегорияНоменклатуры_Key"] == CAT1
    assert p1["ЕдиницаИзмерения_Key"] == "33333333-3333-3333-3333-333333333333"
    assert p1["Вес"] == 0
    assert p1["DeletionMark"] is False
    assert by_key[P3_FOLDER]["IsFolder"] is True


async def test_products_required_filter(client):
    response = await get(
        client,
        "Catalog_Номенклатура",
        params={"$filter": "ТипНоменклатуры eq 'Запас' and IsFolder eq false"},
    )
    body = response.json()
    assert {row["Ref_Key"] for row in body["value"]} == {P1, P2}


async def test_prices_fields_and_filter(client):
    body = (await get(client, "InformationRegister_ЦеныНоменклатуры")).json()
    assert len(body["value"]) == 3
    row = next(r for r in body["value"] if r["Номенклатура_Key"] == P1 and r["ВидЦен_Key"] == PT_RETAIL)
    assert row["Period"] == "2025-03-01T00:00:00"
    assert row["Характеристика_Key"] == NULL_GUID
    assert row["Цена"] == 280.0
    assert row["Актуальность"] is True

    filtered = (
        await get(
            client,
            "InformationRegister_ЦеныНоменклатуры",
            params={"$filter": f"ВидЦен_Key eq '{PT_OPT}'"},
        )
    ).json()
    assert {r["Номенклатура_Key"] for r in filtered["value"]} == {P1}
    assert filtered["value"][0]["Цена"] == 240.0


async def test_stock_balance_fields_and_filter(client):
    body = (await get(client, "AccumulationRegister_ЗапасыНаСкладах/Balance")).json()
    assert len(body["value"]) == 27  # 2 базовые + 25 регрессионных (см. conftest)
    row = next(r for r in body["value"] if r["Номенклатура_Key"] == P1)
    assert row["СтруктурнаяЕдиница_Key"] == WH1
    assert row["Характеристика_Key"] == NULL_GUID
    assert row["Партия_Key"] == NULL_GUID
    assert row["Ячейка_Key"] == NULL_GUID
    assert row["КоличествоBalance"] == 10.5
    assert row["КоличествоИнтBalance"] == 0

    filtered = (
        await get(
            client,
            "AccumulationRegister_ЗапасыНаСкладах/Balance",
            params={"$filter": f"СтруктурнаяЕдиница_Key eq '{WH1}'"},
        )
    ).json()
    assert len(filtered["value"]) == 27
    # отрицательный остаток отдаём как есть (как 1С)
    negative = next(r for r in filtered["value"] if r["Номенклатура_Key"] == P2)
    assert negative["КоличествоBalance"] == -2.0


async def test_attribute_definitions_raw_passthrough(client):
    body = (await get(client, "ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения")).json()
    by_key = {row["Ref_Key"]: row for row in body["value"]}
    # raw заполнен → отдаём как есть
    row = by_key[ATTR1]
    assert row["Заголовок"] == "Цвет товара"
    assert row["ValueType"]["Types"] == ["CatalogRef.ЗначенияСвойствОбъектов"]
    # raw = NULL (весь дамп такой) → собираем минимальный record из плоских колонок
    synthesized = by_key[ATTR2]
    assert synthesized["Description"] == "Материал"
    assert synthesized["Заголовок"] == "Материал"
    assert synthesized["DeletionMark"] is False
    assert synthesized["ValueType"]["Types"] == ["CatalogRef.ЗначенияСвойствОбъектов"]


async def test_attribute_values_filter_by_owner(client):
    body = (
        await get(
            client,
            "Catalog_ЗначенияСвойствОбъектов",
            params={"$filter": f"Owner_Key eq '{ATTR1}'"},
        )
    ).json()
    assert body["value"] == [
        {"Ref_Key": VAL1, "Description": "Красный", "Owner_Key": ATTR1, "DeletionMark": False}
    ]


async def test_product_attributes_filter_guid_and_plain(client):
    for filter_expr in (f"Ref_Key eq guid'{P1}'", f"Ref_Key eq '{P1}'"):
        body = (
            await get(
                client,
                "Catalog_Номенклатура_ДополнительныеРеквизиты",
                params={"$filter": filter_expr},
            )
        ).json()
        assert len(body["value"]) == 2
        by_line = {row["LineNumber"]: row for row in body["value"]}
        first = by_line["1"]
        assert first["Ref_Key"] == P1
        assert first["Свойство_Key"] == ATTR1
        assert first["Значение"] == VAL1
        assert first["Значение_Type"] == "StandardODATA.Catalog_ЗначенияСвойствОбъектов"
        assert first["ТекстоваяСтрока"] == ""
        second = by_line["2"]
        assert second["Значение"] == NULL_GUID
        assert second["Значение_Type"] == "Edm.String"
        assert second["ТекстоваяСтрока"] == "произвольный текст"


async def test_units(client):
    body = (await get(client, "Catalog_КлассификаторЕдиницИзмерения")).json()
    assert body["value"] == [
        {"Ref_Key": "33333333-3333-3333-3333-333333333333", "Description": "шт", "Code": "796 "}
    ]


async def test_price_types(client):
    body = (await get(client, "Catalog_ВидыЦен")).json()
    assert {row["Description"] for row in body["value"]} == {"Розница", "Оптовая"}
    for row in body["value"]:
        assert set(row) == {"Ref_Key", "Description", "DeletionMark"}


async def test_product_files_fields_and_filter(client):
    body = (
        await get(
            client,
            "Catalog_НоменклатураПрисоединенныеФайлы",
            params={"$filter": f"ВладелецФайла_Key eq guid'{P1}'"},
        )
    ).json()
    assert len(body["value"]) == 1
    row = body["value"][0]
    assert row["Ref_Key"] == F1
    assert row["Description"] == "photo1"
    assert row["ВладелецФайла_Key"] == P1
    assert row["Размер"] == "123807"
    assert row["Расширение"] == "jpg"
    assert row["DeletionMark"] is False
    assert row["ДатаСоздания"] == "2021-04-13T14:20:02"


# ─── Пагинация ──────────────────────────────────────────────────────────────


async def test_pagination_top_skip(client):
    first = (await get(client, "Catalog_Номенклатура", params={"$top": 2})).json()["value"]
    second = (
        await get(client, "Catalog_Номенклатура", params={"$top": 2, "$skip": 2})
    ).json()["value"]
    all_rows = (await get(client, "Catalog_Номенклатура")).json()["value"]
    assert len(first) == 2 and len(second) == 2
    assert first + second == all_rows


async def test_default_top_is_100(client):
    body = (await get(client, "Catalog_Номенклатура")).json()
    assert len(body["value"]) == 4  # все 4 товара, top=100 по умолчанию не режет


async def test_pagination_no_loss_no_duplicates(client):
    """Обход Balance мелкими страницами: мультимножество строк = всей фикстуре.

    25 из 27 строк имеют одинаковые organization_key/warehouse_key — с неуникальным
    ORDER BY страницы теряли/дублировали строки (баг живого прогона).
    """
    from collections import Counter

    seen: Counter = Counter()
    skip = 0
    page_size = 7
    while True:
        body = (
            await get(
                client, "AccumulationRegister_ЗапасыНаСкладах/Balance",
                params={"$top": page_size, "$skip": skip},
            )
        ).json()
        if not body["value"]:
            break
        assert len(body["value"]) <= page_size
        for row in body["value"]:
            seen[(row["Номенклатура_Key"], row["КоличествоBalance"])] += 1
        skip += page_size
    assert sum(seen.values()) == 27  # 2 базовые + 25 сгенерированных
    assert all(count == 1 for count in seen.values())  # ни дублей, ни потерь


async def test_ignored_params(client):
    response = await get(
        client,
        "Catalog_ВидыЦен",
        params={"$format": "json", "$select": "Ref_Key", "$orderby": "Description"},
    )
    assert response.status_code == 200
    assert len(response.json()["value"]) == 2


# ─── Бинарь файла ($value) ──────────────────────────────────────────────────


async def test_file_value_placeholder_jpeg(client):
    response = await get(client, f"Catalog_НоменклатураПрисоединенныеФайлы(guid'{F1}')/$value")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    image = Image.open(io.BytesIO(response.content))
    image.verify()

    repeat = await get(client, f"Catalog_НоменклатураПрисоединенныеФайлы(guid'{F1}')/$value")
    assert repeat.content == response.content  # детерминизм


async def test_file_value_unknown_guid_404(client):
    response = await get(
        client, f"Catalog_НоменклатураПрисоединенныеФайлы(guid'{NULL_GUID}')/$value"
    )
    assert response.status_code == 404
    assert "odata.error" in response.json()


def test_placeholder_pool_deterministic_after_warmup():
    """После warmup_pool() (боевой путь, lifespan) ref_key → тот же валидный JPEG из пула."""
    from onec_mock.images import placeholder_jpeg, warmup_pool

    warmup_pool()
    first = placeholder_jpeg(F1)
    Image.open(io.BytesIO(first)).verify()
    assert placeholder_jpeg(F1) == first
    assert placeholder_jpeg(NULL_GUID) != b""
