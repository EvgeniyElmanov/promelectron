"""Unit tests for search_service: settings payload, provisioning, task polling.

Meilisearch SDK is fully mocked — no live service required (PLAN R7).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from meilisearch.errors import MeilisearchError

from src.app.services import search_service
from src.app.services.search_service import (
    SearchTaskError,
    SearchUnavailableError,
)


def _task(uid=1, status="succeeded", error=None):
    return SimpleNamespace(task_uid=uid, status=status, error=error)


class TestIndexSettings:
    def test_filterable_includes_base_and_attr_codes(self):
        payload = search_service.index_settings(["cross_section_mm2", "color"])
        filterable = payload["filterableAttributes"]
        for base in ("price", "stock", "category_id", "categories.lvl0", "categories.lvl1"):
            assert base in filterable
        assert "attrs.cross_section_mm2" in filterable
        assert "attrs.color" in filterable

    def test_searchable_sortable_and_ranking(self):
        payload = search_service.index_settings([])
        assert payload["searchableAttributes"] == ["name", "sku", "description"]
        assert "price" in payload["sortableAttributes"]
        assert "name" in payload["sortableAttributes"]
        rules = payload["rankingRules"]
        assert rules.index("stock:desc") < rules.index("sort")

    def test_typo_tolerance_and_pagination(self):
        payload = search_service.index_settings([])
        assert payload["typoTolerance"]["disableOnNumbers"] is True
        assert payload["pagination"]["maxTotalHits"] == 10000
        assert payload["faceting"]["maxValuesPerFacet"] == 100
        assert payload["faceting"]["sortFacetValuesBy"] == {"*": "count"}

    def test_synonyms_mvp_set(self):
        payload = search_service.index_settings([])
        assert "кабель" in payload["synonyms"]
        assert "провод" in payload["synonyms"]["кабель"]


class TestProvisionIndex:
    def test_creates_index_and_applies_settings_before_documents(self):
        client = MagicMock()
        client.get_index.side_effect = MeilisearchError("index not found")
        client.index.return_value.update_settings.return_value = _task(uid=7)
        client.get_task.return_value = _task(uid=7, status="succeeded")

        search_service.provision_index(client, "products_new", ["color"])

        client.create_index.assert_called_once_with("products_new", {"primaryKey": "id"})
        update = client.index.return_value.update_settings
        update.assert_called_once()
        settings_payload = update.call_args.args[0]
        assert "attrs.color" in settings_payload["filterableAttributes"]

    def test_existing_index_skips_create(self):
        client = MagicMock()
        client.index.return_value.update_settings.return_value = _task(uid=8)
        client.get_task.return_value = _task(uid=8, status="succeeded")

        search_service.provision_index(client, "products", [])

        client.create_index.assert_not_called()
        client.index.return_value.update_settings.assert_called_once()

    def test_failed_settings_task_raises(self):
        client = MagicMock()
        client.index.return_value.update_settings.return_value = _task(uid=9)
        client.get_task.return_value = _task(uid=9, status="failed", error={"message": "boom"})

        with pytest.raises(SearchTaskError):
            search_service.provision_index(client, "products", [])


class TestWaitForTask:
    def test_succeeded_returns(self):
        client = MagicMock()
        client.get_task.return_value = _task(status="succeeded")
        search_service.wait_for_task(client, 1)

    def test_failed_raises(self):
        client = MagicMock()
        client.get_task.return_value = _task(status="failed", error={"message": "x"})
        with pytest.raises(SearchTaskError, match="failed"):
            search_service.wait_for_task(client, 1)

    def test_canceled_raises(self):
        client = MagicMock()
        client.get_task.return_value = _task(status="canceled")
        with pytest.raises(SearchTaskError, match="canceled"):
            search_service.wait_for_task(client, 1)

    def test_timeout_raises(self):
        client = MagicMock()
        client.get_task.return_value = _task(status="processing")
        with pytest.raises(SearchTaskError, match="timed out"):
            search_service.wait_for_task(client, 1, timeout_seconds=0, poll_interval=0)


class TestGetMeiliClient:
    def test_raises_when_not_configured(self, monkeypatch):
        monkeypatch.setattr(
            search_service, "settings", SimpleNamespace(meilisearch_url=None)
        )
        search_service.reset_meili_client()
        with pytest.raises(SearchUnavailableError):
            search_service.get_meili_client()
        search_service.reset_meili_client()
