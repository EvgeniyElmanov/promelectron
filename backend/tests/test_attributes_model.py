"""Smoke-тесты моделей Attribute / ProductAttributeValue (Фаза 4, #120)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.app.models.attribute import Attribute, AttributeValueType, ProductAttributeValue


@pytest.mark.asyncio
async def test_attribute_create_defaults(test_session):
    attr = Attribute(code="cross_section", name="Сечение", value_type=AttributeValueType.number)
    test_session.add(attr)
    await test_session.commit()
    await test_session.refresh(attr)

    assert attr.id is not None
    assert attr.is_filterable is False
    assert attr.sort == 0
    assert attr.unit is None
    assert attr.onec_id is None


@pytest.mark.asyncio
async def test_attribute_code_unique(test_session):
    test_session.add(Attribute(code="brand", name="Бренд"))
    await test_session.commit()
    test_session.add(Attribute(code="brand", name="Бренд дубль"))
    with pytest.raises(IntegrityError):
        await test_session.commit()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_product_attribute_value_upsert_unique(test_session, test_product):
    attr = Attribute(
        code="cross_section",
        name="Сечение",
        value_type=AttributeValueType.number,
        unit="мм²",
    )
    test_session.add(attr)
    await test_session.commit()

    value = ProductAttributeValue(
        product_id=test_product.id,
        attribute_id=attr.id,
        value_number=10.0,
    )
    test_session.add(value)
    await test_session.commit()

    duplicate = ProductAttributeValue(
        product_id=test_product.id,
        attribute_id=attr.id,
        value_number=16.0,
    )
    test_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await test_session.commit()
    await test_session.rollback()


@pytest.mark.asyncio
async def test_product_attribute_value_typed_columns(test_session, test_product):
    number_attr = Attribute(code="length", name="Длина", value_type=AttributeValueType.number)
    text_attr = Attribute(code="color", name="Цвет", value_type=AttributeValueType.string)
    bool_attr = Attribute(code="halogen_free", name="Безгалогенный", value_type=AttributeValueType.bool)
    test_session.add_all([number_attr, text_attr, bool_attr])
    await test_session.commit()

    test_session.add_all(
        [
            ProductAttributeValue(
                product_id=test_product.id, attribute_id=number_attr.id, value_number=1.5
            ),
            ProductAttributeValue(
                product_id=test_product.id, attribute_id=text_attr.id, value_text="чёрный"
            ),
            ProductAttributeValue(
                product_id=test_product.id, attribute_id=bool_attr.id, value_bool=True
            ),
        ]
    )
    await test_session.commit()

    result = await test_session.execute(
        select(ProductAttributeValue).where(ProductAttributeValue.product_id == test_product.id)
    )
    values = {v.attribute_id: v for v in result.scalars().all()}
    assert float(values[number_attr.id].value_number) == 1.5
    assert values[text_attr.id].value_text == "чёрный"
    assert values[bool_attr.id].value_bool is True
    # option_id зарезервирован (attribute_options out of scope) и остаётся NULL
    assert all(v.option_id is None for v in values.values())
