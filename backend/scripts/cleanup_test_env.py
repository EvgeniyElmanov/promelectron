#!/usr/bin/env python3
"""Полная очистка test-окружения перед CI-сидингом каталога (issue #147, D-01/D-02).

Удаляет ВСЕ данные test-стенда, КРОМЕ пользователей:
- каталожные и операционные таблицы public-схемы (TRUNCATE ... RESTART IDENTITY CASCADE);
- схему ``onec_mock`` (пересоздаётся ``init_db`` мока при его рестарте);
- документы индекса ``products`` в Meilisearch (settings индекса сохраняются);
- объекты MinIO (бакет ``onec-intake`` и префикс ``products/`` в ``MINIO_BUCKET``) —
  только при ``STORAGE_BACKEND=minio``; при ``local`` файлы сотрёт rollout restart api
  (emptyDir ``/app/uploads``).

Защита от запуска в prod (тройная, D-02):
1. Скрипт работает только при env ``ALLOW_DESTRUCTIVE_TEST_CLEANUP=true``
   (выставляется ТОЛЬКО в ``infra/helm/stage/test/values.yaml``; в prod-values
   отсутствует → fail-fast).
2. Обязательный аргумент ``--confirm=<namespace>``, сверяемый с env ``POD_NAMESPACE``
   (пробрасывается в api-под через fieldRef metadata.namespace).
3. Job ``seed-test-catalog`` существует только в test-ветке ``deploy.yml``.

Запуск (внутри api-пода):
    python /app/scripts/cleanup_test_env.py --confirm=promelectron-test
"""

import argparse
import asyncio
import os
import sys
from urllib.parse import urlparse

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from src.app.core.config import settings
from src.app.db.database import SessionLocal

# Дочерние → родительские; единый TRUNCATE ... CASCADE снимает вопрос порядка,
# список зафиксирован явно, чтобы случайно не зацепить users / delivery_methods.
# НЕ трогаем: users, user_addresses, social_accounts, email_verification_tokens,
# password_reset_tokens (привязаны к users), delivery_methods (справочные данные
# test-стенда, E2E использует CDEK-виджет, а не эти строки).
TRUNCATE_TABLES = [
    "reviews",
    "favorites",
    "notifications",
    "payments",
    "cdek_status_history",
    "cdek_orders",
    "order_items",
    "orders",
    "recipients",
    "cart_items",
    "carts",
    "jobs",
    "onec_change_log",
    "onec_intake_log",
    "product_attribute_values",
    "product_prices",
    "products",
    "attributes",
    "categories",
    "suppliers",
]

ONEC_MOCK_SCHEMA = "onec_mock"
MEILI_INDEX = "products"
MEILI_STAGING_INDEX = "products_new"


def _fail(message: str) -> None:
    print(f"[CLEANUP] ОТКАЗ: {message}", file=sys.stderr)
    sys.exit(1)


def check_guards(confirm: str) -> None:
    """Fail-fast проверки ДО любых side effects."""
    if os.getenv("ALLOW_DESTRUCTIVE_TEST_CLEANUP", "").lower() != "true":
        _fail(
            "ALLOW_DESTRUCTIVE_TEST_CLEANUP != 'true'. Скрипт предназначен ТОЛЬКО для "
            "test-окружения; в prod-манифестах этот флаг отсутствует by design."
        )
    pod_namespace = os.getenv("POD_NAMESPACE", "")
    if not pod_namespace:
        _fail(
            "POD_NAMESPACE не задан (ожидается fieldRef metadata.namespace в "
            "api-deployment). Отказ: не могу подтвердить окружение."
        )
    if not confirm:
        _fail("Требуется --confirm=<namespace> (например, --confirm=promelectron-test).")
    if confirm != pod_namespace:
        _fail(f"--confirm={confirm!r} не совпадает с POD_NAMESPACE={pod_namespace!r}.")
    if "test" not in pod_namespace:
        _fail(
            f"POD_NAMESPACE={pod_namespace!r} не похож на test-окружение. "
            "Очистка разрешена только в namespace, содержащем 'test'."
        )


async def _table_count(session, table: str) -> int:
    result = await session.execute(text(f'SELECT count(*) FROM "{table}"'))
    return int(result.scalar_one())


async def cleanup_postgres() -> dict[str, tuple[int, int]]:
    counts: dict[str, tuple[int, int]] = {}
    async with SessionLocal() as session:
        db_info = await session.execute(
            text("SELECT current_database(), inet_server_addr(), inet_server_port()")
        )
        db_name, db_host, db_port = db_info.one()
        print(f"[CLEANUP] PostgreSQL: db={db_name} host={db_host}:{db_port}")
        # S004 (defense in depth): позитивная проверка идентичности БД.
        # Имя БД на test-стенде не содержит 'test' (sops-secrets: POSTGRES_DB),
        # поэтому: точное имя можно зафиксировать env-override'ом
        # EXPECTED_TEST_DB_NAME, а без него — отказ, если имя похоже на prod.
        expected_db = os.getenv("EXPECTED_TEST_DB_NAME", "")
        if expected_db:
            if db_name != expected_db:
                _fail(
                    f"current_database()={db_name!r} не совпадает с "
                    f"EXPECTED_TEST_DB_NAME={expected_db!r}. Отказ."
                )
        elif "prod" in db_name.lower():
            _fail(
                f"current_database()={db_name!r} похоже на prod-БД. Отказ: "
                "очистка разрешена только против test-БД."
            )
        print(f"[CLEANUP] users НЕ трогаем: {await _table_count(session, 'users')} строк")

        for table in TRUNCATE_TABLES:
            counts[table] = (await _table_count(session, table), 0)

        tables_sql = ", ".join(f'"{t}"' for t in TRUNCATE_TABLES)
        await session.execute(
            text(f"TRUNCATE {tables_sql} RESTART IDENTITY CASCADE")
        )
        await session.execute(
            text(f"DROP SCHEMA IF EXISTS {ONEC_MOCK_SCHEMA} CASCADE")
        )
        await session.execute(text(f"CREATE SCHEMA {ONEC_MOCK_SCHEMA}"))

        for table in TRUNCATE_TABLES:
            before, _ = counts[table]
            counts[table] = (before, await _table_count(session, table))

        await session.commit()

    print(f"[CLEANUP] Схема {ONEC_MOCK_SCHEMA} пересоздана пустой "
          "(таблицы создаст init_db мока при рестарте)")
    return counts


def cleanup_meilisearch() -> None:
    if not settings.meilisearch_url:
        print("[CLEANUP] Meilisearch: MEILISEARCH_URL не задан — skip")
        return
    import meilisearch
    from meilisearch.errors import MeilisearchApiError

    client = meilisearch.Client(
        settings.meilisearch_url, settings.meilisearch_master_key
    )
    try:
        stats = client.index(MEILI_INDEX).get_stats()
        print(f"[CLEANUP] Meili '{MEILI_INDEX}': {stats.number_of_documents} документов до")
        client.index(MEILI_INDEX).delete_all_documents()
        print(f"[CLEANUP] Meili '{MEILI_INDEX}': delete_all_documents() отправлен "
              "(settings индекса сохранены)")
    except MeilisearchApiError as exc:
        if exc.status_code == 404:
            print(f"[CLEANUP] Meili '{MEILI_INDEX}': индекс отсутствует — ok")
        else:
            raise
    try:
        client.get_index(MEILI_STAGING_INDEX)
    except MeilisearchApiError as exc:
        if exc.status_code != 404:
            raise
    else:
        client.delete_index(MEILI_STAGING_INDEX)
        print(f"[CLEANUP] Meili '{MEILI_STAGING_INDEX}': staging-индекс удалён")


async def _purge_bucket(client, bucket: str, prefix: str = "") -> int:
    """Удалить все объекты бакета (или префикса). Возвращает число удалённых."""
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")
    async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            await client.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            deleted += len(objects)
    return deleted


async def cleanup_minio() -> None:
    if settings.storage_backend != "minio":
        print(f"[CLEANUP] MinIO: STORAGE_BACKEND={settings.storage_backend!r} — skip "
              "(local-файлы сотрёт rollout restart api, emptyDir /app/uploads)")
        return
    from aiobotocore.session import get_session

    session = get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        use_ssl=settings.minio_secure,
    ) as client:
        try:
            n = await _purge_bucket(client, settings.minio_intake_bucket)
            print(f"[CLEANUP] MinIO '{settings.minio_intake_bucket}': удалено {n} объектов")
        except client.exceptions.NoSuchBucket:
            print(f"[CLEANUP] MinIO '{settings.minio_intake_bucket}': бакет отсутствует — ok")
        try:
            n = await _purge_bucket(client, settings.minio_bucket, prefix="products/")
            print(f"[CLEANUP] MinIO '{settings.minio_bucket}/products/': удалено {n} объектов")
        except client.exceptions.NoSuchBucket:
            print(f"[CLEANUP] MinIO '{settings.minio_bucket}': бакет отсутствует — ok")


async def run() -> None:
    counts = await cleanup_postgres()
    # Meili SDK синхронный; вызовы короткие, блокировка скрипта некритична.
    await asyncio.to_thread(cleanup_meilisearch)
    await cleanup_minio()

    print("\n[CLEANUP] Сводка (до -> после):")
    for table, (before, after) in counts.items():
        print(f"  {table}: {before} -> {after}")
    print("[CLEANUP] Готово.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--confirm",
        required=True,
        help="Ожидаемый namespace (должен совпасть с POD_NAMESPACE), напр. promelectron-test",
    )
    args = parser.parse_args()

    check_guards(args.confirm)
    db_host = urlparse(settings.database_url).hostname
    print(f"[CLEANUP] СТАРТ: namespace={os.getenv('POD_NAMESPACE')} "
          f"db_host={db_host} storage_backend={settings.storage_backend!r}")
    asyncio.run(run())


if __name__ == "__main__":
    main()
