"""Regression test: seed_test_catalog.sh не должен вызывать product detail
с trailing slash (route /products/{id} без slash → 307 → curl -sf пустое тело →
JSONDecodeError → misleading FAIL, run 31670580082)."""

import re
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "seed_test_catalog.sh"


def test_product_detail_url_has_no_trailing_slash():
    if not SCRIPT.exists():
        # В backend-контейнере (make test-backend) монтируется только backend/,
        # scripts/ недоступен — регрессионный гард имеет смысл в полном checkout (CI, pre-push).
        pytest.skip("scripts/ci/ недоступен в backend-only контейнере")
    text = SCRIPT.read_text(encoding="utf-8")
    # URL вида .../products/<expr>/ (slash сразу после $FIRST_ID / ${...} / числа)
    bad = re.findall(r'api/v1/products/(?:\$\{?\w+\}?|\d+)/"', text)
    assert not bad, (
        f"product detail вызывается с trailing slash: {bad} — "
        f"route /products/{{id}} без slash, 307 сломает curl -sf"
    )
