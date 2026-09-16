"""HTTP tests for the public search API and admin search endpoints.

Meilisearch is mocked at the service layer (``search_query``); PG and Redis
are real (Docker). Covers: filter expression building, disjunctive
multi-search, range filters, feature-flag gating, caching, trailing slash,
admin guards and idempotent reindex.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.app.models.attribute import Attribute, AttributeValueType
from src.app.services import feature_flags, search_query


@pytest.fixture
async def search_attributes(test_session):
    attrs = [
        Attribute(
            code="cross_section_mm2",
            name="Сечение",
            value_type=AttributeValueType.number,
            unit="мм²",
            is_filterable=True,
            sort=1,
        ),
        Attribute(
            code="color",
            name="Цвет",
            value_type=AttributeValueType.enum,
            is_filterable=True,
            sort=2,
        ),
        Attribute(
            code="internal_note",
            name="Служебный",
            value_type=AttributeValueType.string,
            is_filterable=False,
            sort=3,
        ),
    ]
    test_session.add_all(attrs)
    await test_session.commit()
    return attrs


@pytest.fixture
async def flag_on():
    await feature_flags.set_enabled("catalog_search_meilisearch", True)
    yield
    await feature_flags.set_enabled("catalog_search_meilisearch", False)


def _multi_search_payload(**overrides):
    main = {
        "hits": [
            {
                "id": 1,
                "sku": "USB-C-1M",
                "name": "Кабель USB-C 1м",
                "price": 350.0,
                "stock": 42,
                "category_id": 7,
                "categories": {"lvl0": "Кабели", "lvl1": "Кабели > USB"},
                "attrs": {"cross_section_mm2": 2.5, "color": "чёрный"},
            }
        ],
        "totalHits": 1,
        "totalPages": 1,
        "facetDistribution": {"color": None, "attrs.color": {"чёрный": 1}},
        "facetStats": {
            "price": {"min": 100.0, "max": 900.0},
            "attrs.cross_section_mm2": {"min": 0.5, "max": 10.0},
        },
    }
    main.update(overrides)
    return {"results": [main]}


def _mock_multi_search(monkeypatch, payload):
    mock = AsyncMock(return_value=payload)
    monkeypatch.setattr(search_query, "multi_search_async", mock)
    monkeypatch.setattr(search_query, "get_meili_client", lambda: MagicMock())
    return mock


class TestFeatureFlagGate:
    async def test_flag_off_returns_404(self, client, search_attributes):
        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 404

    async def test_suggestions_flag_off_returns_404(self, client):
        response = await client.get("/api/v1/search/suggestions/", params={"q": "ка"})
        assert response.status_code == 404


class TestSearchEndpoint:
    async def test_basic_search_contract(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        mock = _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get("/api/v1/search/", params={"q": "кабль"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["pages"] == 1
        assert data["items"][0]["name"] == "Кабель USB-C 1м"
        # q is passed through (typo tolerance is Meilisearch-side)
        queries = mock.call_args.args[1]
        assert queries[0]["q"] == "кабль"
        assert queries[0]["page"] == 1
        assert queries[0]["hitsPerPage"] == 20
        # facets: metadata + values/stats per contract
        facets = {f["code"]: f for f in data["facets"]}
        assert facets["price"]["stats"] == {"min": 100.0, "max": 900.0}
        assert facets["cross_section_mm2"]["unit"] == "мм²"
        assert facets["cross_section_mm2"]["stats"] == {"min": 0.5, "max": 10.0}
        assert facets["color"]["values"] == [{"value": "чёрный", "count": 1}]
        assert "internal_note" not in facets
        # F003: only product-card fields are retrieved from Meilisearch
        assert queries[0]["attributesToRetrieve"] == [
            "id", "sku", "name", "price", "stock", "category_id",
            "categories", "attrs", "images", "brand", "created_at",
        ]

    async def test_images_returned_when_present(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        payload = _multi_search_payload()
        payload["results"][0]["hits"][0]["images"] = ["uploads/a.jpg", "uploads/b.jpg"]
        _mock_multi_search(monkeypatch, payload)
        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 200
        assert response.json()["items"][0]["images"] == [
            "uploads/a.jpg",
            "uploads/b.jpg",
        ]

    async def test_images_default_empty_before_reindex(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        """Index built before #137 has no images field — response must not break."""
        _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 200
        assert response.json()["items"][0]["images"] == []
    async def test_raw_document_fields_stay_on_server(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        """F003: stable contract — raw Meilisearch fields are not exposed."""
        payload = _multi_search_payload()
        payload["results"][0]["hits"][0].update(
            {"description": "служебное описание", "onec_id": "guid-123"}
        )
        _mock_multi_search(monkeypatch, payload)
        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["name"] == "Кабель USB-C 1м"
        assert "description" not in item
        assert "onec_id" not in item
        # created_at индексируется для вычисления is_new, но наружу не отдаётся
        assert "created_at" not in item
        assert set(item) == {
            "id", "sku", "name", "price", "stock", "category_id",
            "categories", "attrs", "images",
            "average_rating", "reviews_count", "brand", "is_new", "is_hit",
        }

    async def test_numeric_attr_filter_unquoted(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        mock = _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get(
            "/api/v1/search/", params={"attr.cross_section_mm2": "2.5"}
        )
        assert response.status_code == 200
        queries = mock.call_args.args[1]
        filters = queries[0]["filter"]
        assert ["attrs.cross_section_mm2 IN [2.5]"] in filters

    async def test_multi_select_attr_or_group(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        mock = _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get(
            "/api/v1/search/",
            params=[("attr.color", "чёрный"), ("attr.color", "белый")],
        )
        assert response.status_code == 200
        filters = mock.call_args.args[1][0]["filter"]
        assert ["attrs.color IN ['чёрный', 'белый']"] in filters

    async def test_disjunctive_subquery_excludes_active_group(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        payload = _multi_search_payload()
        # disjunctive subquery for active group "color": other values stay alive
        payload["results"].append(
            {"facetDistribution": {"attrs.color": {"чёрный": 1, "белый": 5}}}
        )
        mock = _mock_multi_search(monkeypatch, payload)
        response = await client.get("/api/v1/search/", params={"attr.color": "чёрный"})
        assert response.status_code == 200

        queries = mock.call_args.args[1]
        assert len(queries) == 2
        sub = queries[1]
        assert sub["limit"] == 0
        assert sub["facets"] == ["attrs.color"]
        # group's own filter is excluded from the subquery
        assert not any(
            (isinstance(f, list) and any("attrs.color" in s for s in f))
            or (isinstance(f, str) and "attrs.color" in f)
            for f in sub["filter"]
        )
        # merged counts come from the subquery (disjunctive semantics, D-08)
        facets = {f["code"]: f for f in response.json()["facets"]}
        assert facets["color"]["values"] == [
            {"value": "чёрный", "count": 1},
            {"value": "белый", "count": 5},
        ]

    async def test_price_range_filter_and_stats(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        mock = _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get(
            "/api/v1/search/", params={"price_min": 100, "price_max": 500}
        )
        assert response.status_code == 200
        filters = mock.call_args.args[1][0]["filter"]
        assert "price 100.0 TO 500.0" in filters

    async def test_attrs_range_filter(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        mock = _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get(
            "/api/v1/search/", params={"attrs_range.cross_section_mm2": "1:4"}
        )
        assert response.status_code == 200
        filters = mock.call_args.args[1][0]["filter"]
        assert "attrs.cross_section_mm2 1.0 TO 4.0" in filters

    async def test_sort_mapping(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        mock = _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get("/api/v1/search/", params={"sort": "price_desc"})
        assert response.status_code == 200
        assert mock.call_args.args[1][0]["sort"] == ["price:desc"]

    async def test_unknown_sort_400(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get("/api/v1/search/", params={"sort": "random"})
        assert response.status_code == 400

    async def test_unknown_attr_code_400(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get(
            "/api/v1/search/", params={"attr.no_such_attr": "x"}
        )
        assert response.status_code == 400

    async def test_non_filterable_attr_400(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get(
            "/api/v1/search/", params={"attr.internal_note": "x"}
        )
        assert response.status_code == 400

    async def test_hits_per_page_validation(
        self, client, search_attributes, flag_on
    ):
        response = await client.get("/api/v1/search/", params={"hits_per_page": 101})
        assert response.status_code == 422

    async def test_trailing_slash_no_redirect(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get("/api/v1/search/")
        assert response.status_code == 200

    async def test_response_cached_60s(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        mock = _mock_multi_search(monkeypatch, _multi_search_payload())
        first = await client.get("/api/v1/search/", params={"q": "кабель"})
        second = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
        assert mock.call_count == 1  # второй запрос — из кэша

    async def test_meilisearch_down_503(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        from src.app.services.search_service import SearchUnavailableError

        monkeypatch.setattr(
            search_query,
            "multi_search_async",
            AsyncMock(side_effect=SearchUnavailableError("down")),
        )
        monkeypatch.setattr(search_query, "get_meili_client", lambda: MagicMock())
        response = await client.get("/api/v1/search/", params={"q": "x"})
        assert response.status_code == 503


class TestSuggestionsEndpoint:
    async def test_contract(self, client, flag_on, monkeypatch):
        search_mock = AsyncMock(
            return_value={
                "hits": [
                    {
                        "id": 1,
                        "name": "Кабель USB-C",
                        "price": 350.0,
                        "images": ["uploads/usb-c.jpg"],
                    }
                ]
            }
        )
        monkeypatch.setattr(search_query, "search_async", search_mock)
        monkeypatch.setattr(search_query, "get_meili_client", lambda: MagicMock())
        response = await client.get(
            "/api/v1/search/suggestions/", params={"q": "каб", "limit": 5}
        )
        assert response.status_code == 200
        assert response.json() == {
            "queries": [],
            "categories": [],
            "brands": [],
            "products": [
                {
                    "id": 1,
                    "name": "Кабель USB-C",
                    "price": 350.0,
                    "image": "uploads/usb-c.jpg",
                }
            ],
        }
        params = search_mock.call_args.args[3]
        assert params["limit"] == 5
        assert params["attributesToRetrieve"] == ["id", "name", "price", "images"]

    async def test_image_null_when_no_images(self, client, flag_on, monkeypatch):
        monkeypatch.setattr(
            search_query,
            "search_async",
            AsyncMock(
                return_value={
                    "hits": [{"id": 2, "name": "Кабель HDMI", "price": 500.0}]
                }
            ),
        )
        monkeypatch.setattr(search_query, "get_meili_client", lambda: MagicMock())
        response = await client.get(
            "/api/v1/search/suggestions/", params={"q": "каб"}
        )
        assert response.status_code == 200
        product = response.json()["products"][0]
        assert product["image"] is None
        assert product["price"] == 500.0


class TestFacetValuesEndpoint:
    async def test_numeric_facet_rejected(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        monkeypatch.setattr(search_query, "get_meili_client", lambda: MagicMock())
        response = await client.get(
            "/api/v1/search/facet-values/", params={"facet": "cross_section_mm2"}
        )
        assert response.status_code == 400

    async def test_enum_facet_search(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        facet_mock = AsyncMock(
            return_value={"facetHits": [{"value": "чёрный", "count": 12}]}
        )
        monkeypatch.setattr(search_query, "facet_search_async", facet_mock)
        monkeypatch.setattr(search_query, "get_meili_client", lambda: MagicMock())
        response = await client.get(
            "/api/v1/search/facet-values/", params={"facet": "color", "q": "чёр"}
        )
        assert response.status_code == 200
        assert response.json() == {"values": [{"value": "чёрный", "count": 12}]}
        assert facet_mock.call_args.args[2] == "attrs.color"


class TestAdminEndpoints:
    async def test_attributes_requires_admin(self, client, user_token):
        response = await client.get(
            "/api/v1/admin/attributes/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    async def test_attributes_list(
        self, client, admin_token, search_attributes
    ):
        response = await client.get(
            "/api/v1/admin/attributes/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        codes = [a["code"] for a in response.json()]
        assert codes == ["cross_section_mm2", "color", "internal_note"]
        assert response.json()[0]["value_type"] == "number"

    async def test_patch_is_filterable_marks_reindex(
        self, client, admin_token, search_attributes
    ):
        attr_id = search_attributes[1].id  # color, is_filterable=True
        response = await client.patch(
            f"/api/v1/admin/attributes/{attr_id}/",
            json={"is_filterable": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_filterable"] is False
        assert data["reindex_required"] is True

    async def test_patch_without_filterable_change(
        self, client, admin_token, search_attributes
    ):
        attr_id = search_attributes[0].id
        response = await client.patch(
            f"/api/v1/admin/attributes/{attr_id}/",
            json={"name": "Сечение кабеля"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["reindex_required"] is False
        assert response.json()["name"] == "Сечение кабеля"

    async def test_patch_unknown_attribute_404(self, client, admin_token):
        response = await client.patch(
            "/api/v1/admin/attributes/999999/",
            json={"name": "x"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    async def test_reindex_idempotent(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        first = await client.post("/api/v1/admin/search/reindex/", headers=headers)
        assert first.status_code == 202
        second = await client.post("/api/v1/admin/search/reindex/", headers=headers)
        assert second.status_code == 200
        assert second.json()["job_id"] == first.json()["job_id"]
        assert first.json()["created"] is True
        assert second.json()["created"] is False

    async def test_reindex_requires_admin(self, client, user_token):
        response = await client.post(
            "/api/v1/admin/search/reindex/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403


class TestSearchCardAggregates:
    """Поля карточки товара в items /api/v1/search/ (pixel-perfect-homepage, D-03).

    ``brand``/``created_at`` приходят из Meilisearch-документа; рейтинг,
    число отзывов и ``is_hit`` обогащаются из БД по ids hits; ``is_new``
    вычисляется от ``created_at`` в момент запроса.
    """

    async def test_items_include_card_fields(
        self,
        client,
        test_session,
        search_attributes,
        flag_on,
        monkeypatch,
        test_category,
        test_supplier,
        test_user,
    ):
        """Hit с brand/created_at в документе + реальные отзывы и оплаченный
        заказ в БД → все 5 полей с корректными значениями."""
        from datetime import datetime, timezone
        from decimal import Decimal

        from src.app.models.order import Order, OrderItem
        from src.app.models.review import Review
        from tests.conftest import make_product

        product = await make_product(
            test_session,
            name="Search Card Product",
            price=100.0,
            stock=5,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await test_session.flush()
        test_session.add_all(
            [
                Review(product_id=product.id, user_id=test_user.id, rating=5, text="Great"),
                Review(product_id=product.id, user_id=test_user.id, rating=3, text="Ok"),
            ]
        )
        order = Order(user_id=test_user.id, total_price=Decimal("100.0"), status="paid")
        test_session.add(order)
        await test_session.flush()
        test_session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                price_at_time=Decimal("100.0"),
            )
        )
        await test_session.commit()

        payload = _multi_search_payload()
        payload["results"][0]["hits"][0].update(
            {
                "id": product.id,
                "brand": "Legrand",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _mock_multi_search(monkeypatch, payload)

        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["brand"] == "Legrand"
        assert item["average_rating"] == 4.0
        assert item["reviews_count"] == 2
        assert item["is_hit"] is True
        assert item["is_new"] is True
        assert "created_at" not in item

    async def test_items_graceful_defaults_before_reindex(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        """Документ старого индекса без brand/created_at → дефолты, ответ валиден."""
        _mock_multi_search(monkeypatch, _multi_search_payload())
        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["brand"] is None
        assert item["average_rating"] == 0.0
        assert item["reviews_count"] == 0
        assert item["is_new"] is False
        assert item["is_hit"] is False

    async def test_is_new_computed_from_created_at(
        self, client, search_attributes, flag_on, monkeypatch
    ):
        """is_new: свежий created_at → true, 31-дневной давности → false."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        payload = _multi_search_payload()
        payload["results"][0]["hits"] = [
            {"id": 900001, "name": "Fresh", "created_at": now.isoformat()},
            {
                "id": 900002,
                "name": "Stale",
                "created_at": (now - timedelta(days=31)).isoformat(),
            },
        ]
        _mock_multi_search(monkeypatch, payload)

        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 200
        by_id = {i["id"]: i for i in response.json()["items"]}
        assert by_id[900001]["is_new"] is True
        assert by_id[900002]["is_new"] is False

    async def test_brand_fallback_from_db_for_hit_without_document_brand(
        self,
        client,
        test_session,
        search_attributes,
        flag_on,
        monkeypatch,
        test_category,
        test_supplier,
    ):
        """Hit без brand в документе (старый индекс) → brand подтягивается из БД;
        hit с brand в документе → значение документа побеждает (review F-02)."""
        from src.app.models.attribute import Attribute, AttributeValueType, ProductAttributeValue
        from tests.conftest import make_product

        product = await make_product(
            test_session,
            name="Brand Fallback Product",
            price=10.0,
            stock=5,
            supplier_id=test_supplier.id,
            category_id=test_category.id,
            is_active=True,
        )
        await test_session.flush()
        attribute = Attribute(
            code="brand-attr", name="Бренд", value_type=AttributeValueType.string
        )
        test_session.add(attribute)
        await test_session.flush()
        test_session.add(
            ProductAttributeValue(
                product_id=product.id,
                attribute_id=attribute.id,
                value_text="DB Brand",
            )
        )
        await test_session.commit()

        payload = _multi_search_payload()
        payload["results"][0]["hits"] = [
            {"id": product.id, "name": "No Doc Brand"},
            {"id": 900003, "name": "Doc Brand Wins", "brand": "Doc Brand"},
        ]
        _mock_multi_search(monkeypatch, payload)

        response = await client.get("/api/v1/search/", params={"q": "кабель"})
        assert response.status_code == 200
        by_id = {i["id"]: i for i in response.json()["items"]}
        assert by_id[product.id]["brand"] == "DB Brand"
        assert by_id[900003]["brand"] == "Doc Brand"
