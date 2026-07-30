"""Тесты генератора CommerceML 2.x (D-05)."""

import io
import zipfile
from xml.etree import ElementTree as ET

from sqlalchemy import select

from onec_mock.commerceml import CommerceML2Generator
from onec_mock.models import ChangeLog, Product


async def _make_changes(session, products):
    return [
        ChangeLog(
            entity_type="price", entity_onec_id=products[0].onec_id, action="update", payload={}
        ),
        ChangeLog(
            entity_type="stock", entity_onec_id=products[1].onec_id, action="update", payload={}
        ),
        ChangeLog(
            entity_type="product",
            entity_onec_id=products[2].onec_id,
            action="delete",
            payload={"name": products[2].name},
        ),
    ]


async def test_package_is_valid_commerceml(seeded_session):
    products = list((await seeded_session.execute(select(Product).limit(3))).scalars())
    changes = await _make_changes(seeded_session, products)

    package = await CommerceML2Generator().build(seeded_session, changes)

    root = ET.fromstring(package.import_xml)
    assert root.tag == "КоммерческаяИнформация"
    assert root.attrib["ВерсияСхемы"] == "2.10"
    assert root.attrib["СодержитТолькоИзменения"] == "true"
    assert root.find("Классификатор") is not None
    assert root.find("Классификатор").find("Группы").findall("Группа")
    assert root.find("Классификатор").find("Свойства").findall("Свойство")
    assert root.find("Каталог").attrib["СодержитТолькоИзменения"] == "true"

    offers = ET.fromstring(package.offers_xml)
    pack = offers.find("ПакетПредложений")
    assert pack is not None
    assert pack.attrib["СодержитТолькоИзменения"] == "true"


async def test_deleted_product_has_deletion_flag(seeded_session):
    products = list((await seeded_session.execute(select(Product).limit(3))).scalars())
    changes = await _make_changes(seeded_session, products)

    package = await CommerceML2Generator().build(seeded_session, changes)

    items = ET.fromstring(package.import_xml).find("Каталог").find("Товары").findall("Товар")
    by_id = {item.find("Ид").text: item for item in items}
    deleted = by_id[products[2].onec_id]
    assert deleted.find("ПометкаУдаления").text == "true"
    # удалённый товар не должен попадать в offers
    offer_ids = {
        o.find("Ид").text
        for o in ET.fromstring(package.offers_xml)
        .find("ПакетПредложений")
        .find("Предложения")
        .findall("Предложение")
    }
    assert products[2].onec_id not in offer_ids


async def test_offers_contain_price_and_stock(seeded_session):
    products = list((await seeded_session.execute(select(Product).limit(3))).scalars())
    changes = await _make_changes(seeded_session, products)

    package = await CommerceML2Generator().build(seeded_session, changes)

    offers = (
        ET.fromstring(package.offers_xml)
        .find("ПакетПредложений")
        .find("Предложения")
        .findall("Предложение")
    )
    by_id = {o.find("Ид").text: o for o in offers}
    offer = by_id[products[0].onec_id]
    price = offer.find("Цены").find("Цена").find("ЦенаЗаЕдиницу").text
    assert float(price) == float(products[0].price)
    assert int(offer.find("Количество").text) == products[0].stock


async def test_zip_contains_both_files(seeded_session):
    products = list((await seeded_session.execute(select(Product).limit(2))).scalars())
    changes = await _make_changes(seeded_session, products + products[:1])

    package = await CommerceML2Generator().build(seeded_session, changes)

    archive = zipfile.ZipFile(io.BytesIO(package.zip_bytes))
    assert set(archive.namelist()) == {"import.xml", "offers.xml"}
    # содержимое ZIP идентично строковым представлениям
    assert archive.read("import.xml").decode() == package.import_xml
    assert archive.read("offers.xml").decode() == package.offers_xml
