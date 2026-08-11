#!/usr/bin/env python3
"""Загрузка реальных фото товаров на test-стенд (issue #147, D-08).

Источник фото — Wikimedia Commons (манифест ``product_images.json`` рядом со
скриптом, лицензии/авторы зафиксированы в манифесте). Загрузка через
``POST /api/v1/products/{id}/images`` под токеном **seed-supplier** (endpoint
требует supplier-роль и владение товаром — товары intake принадлежат ему через
``ONEC_DEFAULT_SUPPLIER_ID=1``).

Запуск:
    python3 scripts/ci/upload_product_images.py \
        --api https://api.promelectron-test.aidrivencode.ru

Идемпотентно: товары, у которых уже есть images, пропускаются.
Exit code: 1, если доля failed > 20% от товаров-кандидатов.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB — лимит _validate_image/products.py
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
RETRIES = 3
FAIL_THRESHOLD = 0.20
COMMONS_UA = "PromelectronCI-seed/1.0 (https://github.com/AutonomaCo/promelectron)"


def log(msg: str) -> None:
    print(f"[images] {msg}", flush=True)


def find_group(manifest: dict, product_name: str) -> dict | None:
    """Первый match по порядку групп (специфичные идут раньше общих)."""
    name = product_name.lower()
    for group in manifest["groups"]:
        if any(pattern in name for pattern in group["match"]):
            return group
    return None


def download_image(client: httpx.Client, url: str) -> tuple[bytes, str] | None:
    """Скачать фото с retry. Возвращает (content, ext) или None."""
    for attempt in range(1, RETRIES + 1):
        try:
            resp = client.get(url, follow_redirects=True, timeout=60)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                log(f"  не image content-type={content_type!r}: {url}")
                return None
            if len(resp.content) > MAX_FILE_SIZE:
                log(f"  слишком большой файл ({len(resp.content)} байт): {url}")
                return None
            ext = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
            }.get(content_type.split(";")[0].strip())
            if ext not in ALLOWED_EXTENSIONS:
                log(f"  неподдерживаемый тип {content_type!r}: {url}")
                return None
            return resp.content, ext
        except httpx.HTTPError as exc:
            log(f"  попытка {attempt}/{RETRIES}: {type(exc).__name__}: {exc}")
            time.sleep(2 * attempt)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--api",
        default="https://api.promelectron-test.aidrivencode.ru",
        help="Base URL API (без trailing slash)",
    )
    parser.add_argument(
        "--manifest",
        default=str(Path(__file__).with_name("product_images.json")),
        help="Путь к product_images.json",
    )
    args = parser.parse_args()
    api = args.api.rstrip("/")

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    supplier_email = os.getenv("SEED_SUPPLIER_EMAIL", "seed-supplier@example.com")
    supplier_password = os.getenv("SEED_SUPPLIER_PASSWORD", "seedpassword123")

    with httpx.Client() as client:
        # 1. Login seed-supplier
        resp = client.post(
            f"{api}/api/v1/auth/login/",
            json={"email": supplier_email, "password": supplier_password},
            timeout=30,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        log("login seed-supplier: OK")

        # 2. Список товаров (пагинация)
        products: list[dict] = []
        skip = 0
        while True:
            resp = client.get(
                f"{api}/api/v1/products/", params={"skip": skip, "limit": 100}, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            products.extend(data["items"])
            if len(products) >= data["total"] or not data["items"]:
                break
            skip += len(data["items"])
        log(f"товаров в каталоге: {len(products)}")

        # 3. По товарам: match → download → upload
        uploaded = skipped = failed = 0
        commons = httpx.Client(headers={"User-Agent": COMMONS_UA})
        for product in products:
            pid, name = product["id"], product["name"]
            if product.get("images"):
                skipped += 1
                continue
            group = find_group(manifest, name)
            if not group:
                log(f"  NO MATCH: {name!r} — пропуск")
                skipped += 1
                continue
            candidates = list(group["images"]) + [group["fallback"]]
            image = None
            for candidate in candidates:
                image = download_image(commons, candidate["url"])
                if image:
                    break
                log(f"  fallback после неудачи: {candidate['file']}")
            if not image:
                log(f"  FAILED download: {name!r} (id={pid})")
                failed += 1
                continue
            content, ext = image
            try:
                resp = client.post(
                    f"{api}/api/v1/products/{pid}/images",
                    headers=auth,
                    files={"file": (f"product_{pid}{ext}", content, f"image/{ext[1:]}")},
                    timeout=60,
                )
                resp.raise_for_status()
                uploaded += 1
                log(f"  OK: {name!r} (id={pid}) <- {candidates[0]['file']}")
            except httpx.HTTPError as exc:
                log(f"  FAILED upload: {name!r} (id={pid}): {exc}")
                failed += 1
        commons.close()

    total = uploaded + failed
    log(f"ИТОГ: uploaded={uploaded} skipped={skipped} failed={failed}")
    if total and failed / total > FAIL_THRESHOLD:
        log(f"доля failed {failed}/{total} > {FAIL_THRESHOLD:.0%} — FAIL")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
