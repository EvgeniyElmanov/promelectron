"""Regression test: seed_test_catalog.sh не должен вызывать product detail
с trailing slash (route /products/{id} без slash → 307 → curl -sf пустое тело →
JSONDecodeError → misleading FAIL, run 31670580082)."""

import re
from pathlib import Path

import pytest

# Кандидаты расположения скрипта:
# 1. repo-root рядом с backend/ — host-прогон из полного checkout (CI, pre-push);
# 2. /scripts/ci — контейнерный layout, если repo scripts смонтированы в /scripts.
_CANDIDATES_RAW = [
    Path(__file__).resolve().parents[2] / "scripts" / "ci" / "seed_test_catalog.sh",
    Path("/scripts/ci/seed_test_catalog.sh"),
]
# В контейнере оба кандидата могут схлопнуться в один путь — дедупликация.
_CANDIDATES = list(dict.fromkeys(_CANDIDATES_RAW))

SCRIPT = next((p for p in _CANDIDATES if p.is_file()), None)


def test_product_detail_url_has_no_trailing_slash():
    if SCRIPT is None:
        # В backend-контейнере (make test-backend) монтируется только backend/,
        # scripts/ недоступен — регрессионный гард имеет смысл в полном checkout.
        candidates = ", ".join(str(p) for p in _CANDIDATES)
        pytest.skip(f"seed_test_catalog.sh недоступен в этом окружении (искали: {candidates})")
    text = SCRIPT.read_text(encoding="utf-8")
    # URL вида .../products/<expr>/ (slash сразу после $FIRST_ID / ${...} / числа)
    bad = re.findall(r'api/v1/products/(?:\$\{?\w+\}?|\d+)/"', text)
    assert not bad, (
        f"product detail вызывается с trailing slash: {bad} — "
        f"route /products/{{id}} без slash, 307 сломает curl -sf"
    )
