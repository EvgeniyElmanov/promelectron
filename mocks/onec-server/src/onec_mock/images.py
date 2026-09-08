"""Детерминированный placeholder JPEG для $value присоединённых файлов.

Бинарников в дампе нет — генерируем цветную плашку из ref_key (Pillow).
"""

import hashlib
import io

from PIL import Image, ImageDraw

_WIDTH = 320
_HEIGHT = 240


def placeholder_jpeg(ref_key: str) -> bytes:
    digest = hashlib.md5(ref_key.encode()).digest()  # noqa: S324 — не криптография, а детерминизм цвета
    background = (digest[0], digest[1], digest[2])
    image = Image.new("RGB", (_WIDTH, _HEIGHT), background)
    draw = ImageDraw.Draw(image)
    draw.text((10, _HEIGHT // 2), ref_key, fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()
