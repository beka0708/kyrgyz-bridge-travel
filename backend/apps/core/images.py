"""Responsive images: WebP variants for srcset and a JPEG for social previews.

Variants live next to the media files under `cache/` and are created once per source file
(in the background after an admin save, or on first render as a fallback).
"""

import hashlib
import io
import logging
import threading
from dataclasses import dataclass
from pathlib import PurePosixPath

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

WIDTHS = (160, 480, 960, 1600, 2560)  # 160: avatars and logos; 2560: full-width on retina
WEBP_QUALITY = 80
OG_SIZE = (1200, 630)
CACHE_DIR = "cache"


@dataclass(frozen=True)
class Variant:
    url: str
    width: int


def _cache_name(source_name: str, suffix: str) -> str:
    # The hash keeps names unique even if two folders hold files with the same name.
    path = PurePosixPath(source_name)
    digest = hashlib.sha1(source_name.encode()).hexdigest()[:8]
    return f"{CACHE_DIR}/{path.parent}/{path.stem}-{digest}-{suffix}"


def _open(fieldfile) -> Image.Image:
    with fieldfile.storage.open(fieldfile.name, "rb") as fh:
        image = Image.open(fh)
        image.load()
    # Phones store rotation in EXIF; apply it so photos are not sideways.
    return ImageOps.exif_transpose(image)


def _source_width(fieldfile) -> int:
    key = f"imgw:{fieldfile.name}"
    width = cache.get(key)
    if width is None:
        with fieldfile.storage.open(fieldfile.name, "rb") as fh:
            image = Image.open(fh)
            width, height = image.size
            if ImageOps.exif_transpose(image).size != (width, height):
                width = height
        cache.set(key, width, 60 * 60 * 24 * 30)
    return width


def target_widths(source_width: int) -> list[int]:
    """Standard widths below the source, plus the source itself if it is small (no upscaling)."""
    widths = [w for w in WIDTHS if w < source_width]
    if len(widths) < len(WIDTHS):
        widths.append(min(source_width, WIDTHS[-1]))
    return widths


def _save(storage, name: str, image: Image.Image, fmt: str, **options) -> None:
    buffer = io.BytesIO()
    image.save(buffer, fmt, **options)
    if storage.exists(name):
        storage.delete(name)
    storage.save(name, ContentFile(buffer.getvalue()))


def variants(fieldfile) -> list[Variant]:
    """WebP variants (url, width) for srcset; creates the missing ones.

    The result is cached: uploads get unique names, so a name always maps to the same file.
    """
    key = f"imgv:{fieldfile.name}"
    cached = cache.get(key)
    if cached is not None:
        return [Variant(url, width) for url, width in cached]
    found = _build_variants(fieldfile)
    cache.set(key, [(v.url, v.width) for v in found], 60 * 60 * 24 * 30)
    return found


def _build_variants(fieldfile) -> list[Variant]:
    storage = fieldfile.storage
    widths = target_widths(_source_width(fieldfile))
    names = {w: _cache_name(fieldfile.name, f"{w}.webp") for w in widths}
    missing = [w for w, name in names.items() if not storage.exists(name)]
    if missing:
        image = _open(fieldfile)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        for width in missing:
            resized = image.copy()
            resized.thumbnail((width, width * 10), Image.Resampling.LANCZOS)
            _save(storage, names[width], resized, "WEBP", quality=WEBP_QUALITY, method=6)
    return [Variant(storage.url(names[w]), w) for w in widths]


def og_image(fieldfile) -> str:
    """1200×630 JPEG cropped to fill, for Open Graph previews (WhatsApp, Telegram, Facebook)."""
    storage = fieldfile.storage
    name = _cache_name(fieldfile.name, "og.jpg")
    if not storage.exists(name):
        image = ImageOps.fit(_open(fieldfile).convert("RGB"), OG_SIZE, Image.Resampling.LANCZOS)
        _save(storage, name, image, "JPEG", quality=85, optimize=True, progressive=True)
    return storage.url(name)


def safe_variants(fieldfile) -> list[Variant]:
    """Never break a page because of a broken upload: fall back to the original file."""
    try:
        return variants(fieldfile)
    except Exception:
        logger.exception("Could not build image variants for %s", fieldfile.name)
        return [Variant(fieldfile.url, 0)]


def warm(fieldfiles) -> None:
    """Build variants for freshly saved images in a background thread."""
    files = [f for f in fieldfiles if f]
    if not files or not getattr(settings, "IMAGE_WARMUP", True):
        return

    def run():
        for fieldfile in files:
            safe_variants(fieldfile)

    threading.Thread(target=run, daemon=True).start()
