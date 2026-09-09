"""Детерминированный placeholder JPEG для $value присоединённых файлов.

Бинарников в дампе нет — отдаём цветную плашку (Pillow). Генерация JPEG —
CPU-bound и в async-хендлере блокирует event loop: под конкурентным pull-синком
(13K файлов) мок на лимите 200m CPU не успевал отвечать на /health/ и kubelet
рестартовал контейнер. Поэтому Pillow работает один раз на старте: строится пул
из _POOL_SIZE вариантов, а на запрос остаётся O(1) lookup по md5(ref_key).
"""

import hashlib
import io

from PIL import Image, ImageDraw

_WIDTH = 320
_HEIGHT = 240
_POOL_SIZE = 256

_pool: list[bytes] | None = None


def _render_jpeg(label: str) -> bytes:
    digest = hashlib.md5(label.encode()).digest()  # noqa: S324 — не криптография, а детерминизм цвета
    background = (digest[0], digest[1], digest[2])
    image = Image.new("RGB", (_WIDTH, _HEIGHT), background)
    draw = ImageDraw.Draw(image)
    draw.text((10, _HEIGHT // 2), label, fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def warmup_pool() -> None:
    """Предгенерировать пул placeholder-вариантов. Вызывать на старте приложения."""
    global _pool
    if _pool is None:
        _pool = [_render_jpeg(f"placeholder-{i}") for i in range(_POOL_SIZE)]


def placeholder_jpeg(ref_key: str) -> bytes:
    """Детерминированный JPEG для ref_key: вариант из пула по md5(ref_key).

    До warmup_pool() (тесты без lifespan) — рендер на месте, поведение прежнее.
    """
    pool = _pool
    if pool is None:
        return _render_jpeg(ref_key)
    idx = hashlib.md5(ref_key.encode()).digest()[3]  # noqa: S324 — детерминизм, не криптография
    return pool[idx]
