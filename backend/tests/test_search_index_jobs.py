"""Tests for search document build and indexing jobs (real PG, mocked Meilisearch).

Covers: typed attribute document build (D-10), categories denormalization
(D-07), partial update + delete of soft-deleted (D-06), full reindex swap
flow order (settings BEFORE documents → swap → delete old), failure
propagation for job retry, review fixes: sync SDK calls off the event loop
(F001), no live settings on the serving index (F002), compensation reindex
of products changed during the swap window (F004).
"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from src.app.models.attribute import (
    Attribute,
    AttributeValueType,
    ProductAttributeValue,
)
from src.app.models.category import Category
from src.app.models.job import Job
from src.app.models.product import Product
from src.app.services import search_indexing
from src.app.services.search_service import SearchTaskError
from src.app.workers import job_worker


def _task(uid=1, status="succeeded", error=None):
    return SimpleNamespace(task_uid=uid, status=status, error=error)


def _client_mock(task_status="succeeded", error=None):
    """Sync Meilisearch client double: every write returns an awaited task."""
    client = MagicMock()
    client.index.return_value.add_documents.return_value = _task(uid=1)
    client.index.return_value.delete_documents.return_value = _task(uid=2)
    client.index.return_value.update_settings.return_value = _task(uid=3)
    client.swap_indexes.return_value = _task(uid=4)
    client.delete_index.return_value = _task(uid=5)
    client.get_task.return_value = _task(status=task_status, error=error)
    return client


@pytest.fixture
async def catalog(test_session, test_supplier):
    """Category tree (root + child), two products and typed attributes."""
    from sqlalchemy import select

    from src.app.models.supplier import Supplier

    result = await test_session.execute(
        select(Supplier).where(Supplier.user_id == test_supplier.id)
    )
    supplier = result.scalars().first()

    root = Category(name="Кабели", is_active=True)
    child = Category(name="USB", is_active=True)
    test_session.add_all([root, child])
    await test_session.flush()
    child.parent_id = root.id

    product = Product(
        name="Кабель USB-C 1м",
        description="Кабель для зарядки",
        sku="USB-C-1M",
        price=350.00,
        stock=42,
        category_id=child.id,
        supplier_id=supplier.id,
        is_active=True,
    )
    deleted = Product(
        name="Старый кабель",
        price=100.00,
        stock=0,
        category_id=root.id,
        supplier_id=supplier.id,
        is_active=False,
    )
    test_session.add_all([product, deleted])
    await test_session.flush()

    attr_number = Attribute(
        code="cross_section_mm2",
        name="Сечение",
        value_type=AttributeValueType.number,
        unit="мм²",
        is_filterable=True,
    )
    attr_bool = Attribute(
        code="shielded",
        name="Экранирование",
        value_type=AttributeValueType.bool,
        is_filterable=False,
    )
    attr_text = Attribute(
        code="color",
        name="Цвет",
        value_type=AttributeValueType.string,
        is_filterable=True,
    )
    test_session.add_all([attr_number, attr_bool, attr_text])
    await test_session.flush()

    test_session.add_all(
        [
            ProductAttributeValue(
                product_id=product.id,
                attribute_id=attr_number.id,
                value_number=2.5,
            ),
            ProductAttributeValue(
                product_id=product.id, attribute_id=attr_bool.id, value_bool=True
            ),
            ProductAttributeValue(
                product_id=product.id,
                attribute_id=attr_text.id,
                value_text="чёрный",
            ),
        ]
    )
    await test_session.commit()
    return SimpleNamespace(
        root=root, child=child, product=product, deleted=deleted,
        attr_number=attr_number, attr_text=attr_text,
    )


class TestBuildProductDocuments:
    async def test_document_shape_and_typed_attrs(self, test_session, catalog):
        docs, deleted = await search_indexing.build_product_documents(
            test_session, [catalog.product.id, catalog.deleted.id, 999999]
        )
        assert len(docs) == 1
        assert sorted(deleted) == sorted([catalog.deleted.id, 999999])

        doc = docs[0]
        assert doc["id"] == catalog.product.id
        assert doc["sku"] == "USB-C-1M"
        assert doc["name"] == "Кабель USB-C 1м"
        assert doc["price"] == 350.0
        assert doc["stock"] == 42
        assert doc["category_id"] == catalog.child.id
        assert doc["categories"] == {"lvl0": "Кабели", "lvl1": "Кабели > USB"}
        # Typed attrs (D-10): number → float, bool → bool, text → str
        assert doc["attrs"]["cross_section_mm2"] == 2.5
        assert isinstance(doc["attrs"]["cross_section_mm2"], float)
        assert doc["attrs"]["shielded"] is True
        assert doc["attrs"]["color"] == "чёрный"

    async def test_root_category_has_lvl0_only(self, test_session, catalog):
        catalog.product.category_id = catalog.root.id
        await test_session.commit()
        docs, _ = await search_indexing.build_product_documents(
            test_session, [catalog.product.id]
        )
        assert docs[0]["categories"] == {"lvl0": "Кабели"}

    async def test_empty_input(self, test_session):
        docs, deleted = await search_indexing.build_product_documents(test_session, [])
        assert docs == [] and deleted == []


class TestSearchIndexProductsHandler:
    async def test_partial_update_and_delete(
        self, test_session, catalog, monkeypatch
    ):
        client = _client_mock()
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)

        job = Job(
            job_type="SEARCH_INDEX_PRODUCTS",
            payload={"product_ids": [catalog.product.id, catalog.deleted.id]},
        )
        test_session.add(job)
        await test_session.commit()

        await job_worker.handle_search_index_products(job, test_session)

        # Upsert only the active document
        add = client.index.return_value.add_documents
        add.assert_called_once()
        docs = add.call_args.args[0]
        assert [d["id"] for d in docs] == [catalog.product.id]
        # Soft-deleted product goes to delete-batch
        delete = client.index.return_value.delete_documents
        delete.assert_called_once_with([catalog.deleted.id])
        assert "indexed=1" in job.processing_log[-1]
        assert "deleted=1" in job.processing_log[-1]

    async def test_empty_payload_is_noop(self, test_session, monkeypatch):
        client = _client_mock()
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)
        job = Job(job_type="SEARCH_INDEX_PRODUCTS", payload={"product_ids": []})
        test_session.add(job)
        await test_session.commit()

        await job_worker.handle_search_index_products(job, test_session)
        client.index.assert_not_called()

    async def test_batches_of_1000(self, test_session, catalog, monkeypatch):
        client = _client_mock()
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)
        docs = [{"id": i, "name": f"p{i}", "price": 1.0} for i in range(2500)]
        indexed = search_indexing.index_products_partial(
            client, docs, batch_size=1000
        )
        assert indexed == 2500
        assert client.index.return_value.add_documents.call_count == 3


class TestSearchReindexFullHandler:
    async def test_swap_flow_order(self, test_session, catalog, monkeypatch):
        client = _client_mock()
        # indexes do not exist yet → ensure/provision creates them
        from meilisearch.errors import MeilisearchError

        client.get_index.side_effect = MeilisearchError("index not found")
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)

        job = Job(job_type="SEARCH_REINDEX_FULL", payload={})
        test_session.add(job)
        await test_session.commit()

        await job_worker.handle_search_reindex_full(job, test_session)

        # Settings applied to products_new BEFORE any documents: find the
        # first add_documents call and the update_settings calls in order.
        calls = client.mock_calls
        names = [c[0] for c in calls]
        first_settings = next(i for i, n in enumerate(names) if n.endswith("update_settings"))
        first_docs = next(i for i, n in enumerate(names) if n.endswith("add_documents"))
        assert first_settings < first_docs

        # Documents went to products_new
        add_calls = client.index.return_value.add_documents.call_args_list
        assert add_calls, "expected document batches"
        # Atomic swap products ↔ products_new, then old index dropped
        client.swap_indexes.assert_called_once_with(
            [{"indexes": ["products", "products_new"]}]
        )
        client.delete_index.assert_called_once_with("products_new")
        assert "indexed" in job.processing_log[-1]

    async def test_serving_index_settings_not_touched(
        self, test_session, catalog, monkeypatch
    ):
        """F002: update_settings applies ONLY to products_new; the serving
        index gets ensure-exists (get/create) without live settings."""
        client = _client_mock()
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)

        job = Job(job_type="SEARCH_REINDEX_FULL", payload={})
        test_session.add(job)
        await test_session.commit()

        await job_worker.handle_search_reindex_full(job, test_session)

        # Both indexes are ensured to exist (swap fails on a missing index)
        ensured = {c.args[0] for c in client.get_index.call_args_list}
        assert ensured == {"products", "products_new"}
        # Every client.index(<uid>) call (settings + documents) targets the
        # staging index — the serving index is never touched directly
        index_uids = {c.args[0] for c in client.index.call_args_list}
        assert index_uids == {"products_new"}
        client.index.return_value.update_settings.assert_called_once()

    async def test_sync_sdk_calls_run_via_to_thread(
        self, test_session, catalog, monkeypatch
    ):
        """F001: blocking sync SDK calls never run on the event loop."""
        client = _client_mock()
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)

        real_to_thread = asyncio.to_thread
        seen: list[str] = []

        async def spy(func, *args, **kwargs):
            seen.append(repr(func))
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(asyncio, "to_thread", spy)

        job = Job(job_type="SEARCH_REINDEX_FULL", payload={})
        test_session.add(job)
        await test_session.commit()

        await job_worker.handle_search_reindex_full(job, test_session)

        names = " ".join(seen)
        for token in (
            "ensure_index_exists",
            "provision_index",
            "swap_indexes",
            "delete_index",
            "wait_for_task",
        ):
            assert token in names, f"{token} was not dispatched via asyncio.to_thread"

    async def test_failed_task_aborts_before_swap(
        self, test_session, catalog, monkeypatch
    ):
        client = _client_mock(task_status="failed", error={"message": "boom"})
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)

        job = Job(job_type="SEARCH_REINDEX_FULL", payload={})
        test_session.add(job)
        await test_session.commit()

        with pytest.raises(SearchTaskError):
            await job_worker.handle_search_reindex_full(job, test_session)

        client.swap_indexes.assert_not_called()
        client.delete_index.assert_not_called()

    async def test_no_compensation_job_when_nothing_changed(
        self, test_session, catalog, monkeypatch
    ):
        """F004: no products changed during reindex → no compensation job."""
        client = _client_mock()
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)

        job = Job(job_type="SEARCH_REINDEX_FULL", payload={})
        test_session.add(job)
        await test_session.commit()

        await job_worker.handle_search_reindex_full(job, test_session)

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
        assert result.scalars().all() == []
        assert "reindexed_after_swap" not in job.processing_log[-1]

    async def test_compensation_job_for_products_changed_during_reindex(
        self, test_session, catalog, monkeypatch
    ):
        """F004: a product updated while the swap-reindex ran is re-enqueued
        for partial indexing after the swap (watermark = updated_at)."""
        client = _client_mock()
        monkeypatch.setattr(job_worker, "get_meili_client", lambda: client)

        real_reindex_full = job_worker.reindex_full

        async def reindex_and_touch(db, client_arg, **kwargs):
            # Simulate a 1C partial update landing mid-reindex
            catalog.product.price = 999.0
            await db.flush()
            return await real_reindex_full(db, client_arg, **kwargs)

        monkeypatch.setattr(job_worker, "reindex_full", reindex_and_touch)

        job = Job(job_type="SEARCH_REINDEX_FULL", payload={})
        test_session.add(job)
        await test_session.commit()

        await job_worker.handle_search_reindex_full(job, test_session)

        result = await test_session.execute(
            select(Job).where(Job.job_type == "SEARCH_INDEX_PRODUCTS")
        )
        compensation = result.scalars().all()
        assert len(compensation) == 1
        assert compensation[0].payload["product_ids"] == [catalog.product.id]
        assert "'reindexed_after_swap': 1" in job.processing_log[-1]


class TestFindProductsUpdatedSince:
    async def test_watermark_filters_old_rows(self, test_session, catalog):
        watermark = datetime.now(timezone.utc)
        catalog.product.price = 500.0
        await test_session.flush()

        ids = await search_indexing.find_products_updated_since(
            test_session, watermark
        )
        assert ids == [catalog.product.id]

    async def test_includes_soft_deleted(self, test_session, catalog):
        watermark = datetime.now(timezone.utc)
        catalog.deleted.stock = 5
        await test_session.flush()

        ids = await search_indexing.find_products_updated_since(
            test_session, watermark
        )
        # soft-deleted products are included — the partial handler routes
        # them to delete-batch
        assert catalog.deleted.id in ids
