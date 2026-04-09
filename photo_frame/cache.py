"""
cache.py — Pre-resize photos to screen resolution and cache as JPEG.

Eliminates the expensive per-display decode/scale cycle on slow hardware
(e.g. Raspberry Pi) by doing the heavy work once and storing the result.
"""
import hashlib
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps

import config

log = logging.getLogger(__name__)


def _cache_key(photo_path: str) -> str:
    """Deterministic cache filename based on path + mtime."""
    try:
        mtime = os.path.getmtime(photo_path)
    except OSError:
        mtime = 0
    raw = f"{photo_path}|{mtime}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16] + ".jpg"


def get_cached_path(photo_path: str) -> Optional[str]:
    """Return the cached JPEG path if it exists, else None."""
    cached = os.path.join(config.CACHE_DIR, _cache_key(photo_path))
    return cached if os.path.exists(cached) else None


def cache_photo(photo_path: str) -> Optional[str]:
    """
    Resize *photo_path* to screen resolution and save as JPEG.
    Returns the cached file path, or None on failure.
    Skips if already cached.
    """
    cached = os.path.join(config.CACHE_DIR, _cache_key(photo_path))
    if os.path.exists(cached):
        return cached

    try:
        sw, sh = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        with Image.open(photo_path) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            # Scale to COVER the screen (no black bars), then centre-crop to exact size
            iw, ih = img.size
            scale = max(sw / iw, sh / ih)
            new_w, new_h = int(iw * scale), int(ih * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - sw) // 2
            top  = (new_h - sh) // 2
            img = img.crop((left, top, left + sw, top + sh))
            os.makedirs(config.CACHE_DIR, exist_ok=True)
            img.save(cached, "JPEG", quality=config.CACHE_QUALITY)
        log.info("Cached: %s", os.path.basename(photo_path))
        return cached
    except Exception as e:
        log.warning("Failed to cache %s: %s", photo_path, e)
        return None


def build_cache(photo_paths: list[str]) -> None:
    """Process all photos, skipping already-cached ones."""
    total = len(photo_paths)
    done = 0
    for i, path in enumerate(photo_paths):
        if get_cached_path(path):
            done += 1
            continue
        cache_photo(path)
        done += 1
        # Yield CPU between photos so the display loop stays responsive
        time.sleep(0.15)
        if done % 10 == 0:
            log.info("Cache progress: %d / %d", done, total)

    log.info("Cache complete: %d / %d photos", done, total)


class CacheBuilder(threading.Thread):
    """Background thread that caches photos without blocking the main loop."""

    def __init__(self, photo_paths: list[str]):
        super().__init__(daemon=True)
        self._paths = photo_paths

    def run(self):
        log.info("Background cache build started (%d photos)", len(self._paths))
        build_cache(self._paths)
