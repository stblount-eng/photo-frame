"""
scanner.py — Photo discovery and EXIF indexing.

Scans PHOTOS_DIR recursively for supported image files,
reads DateTimeOriginal from EXIF where available, and
returns a sorted list of PhotoEntry objects.
"""
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image
from PIL.ExifTags import TAGS

import config

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".tif"}

EXIF_TAG_MAP = {v: k for k, v in TAGS.items()}
DATETIME_TAG = EXIF_TAG_MAP.get("DateTimeOriginal", 36867)


@dataclass(order=True)
class PhotoEntry:
    """Metadata for a single photo."""
    path: str = field(compare=False)
    taken_at: Optional[datetime] = field(compare=False, default=None)
    width: int = field(compare=False, default=0)
    height: int = field(compare=False, default=0)
    # Used for sorting / grouping
    sort_key: float = field(init=False)

    def __post_init__(self):
        ts = self.taken_at.timestamp() if self.taken_at else 0.0
        object.__setattr__(self, "sort_key", ts)

    @property
    def aspect_ratio(self) -> float:
        if self.height == 0:
            return 1.0
        return self.width / self.height

    @property
    def fit_score(self) -> float:
        """
        How well this photo fills the screen without cropping.
        1.0 = perfect fit. Lower = more wasted space.
        """
        screen_ar = config.SCREEN_WIDTH / config.SCREEN_HEIGHT
        photo_ar = self.aspect_ratio
        return min(screen_ar, photo_ar) / max(screen_ar, photo_ar)


def _read_exif_datetime(path: str) -> Optional[datetime]:
    """Return DateTimeOriginal from EXIF, or None."""
    try:
        with Image.open(path) as img:
            exif_data = img._getexif()
            if exif_data:
                raw = exif_data.get(DATETIME_TAG)
                if raw:
                    return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def _read_dimensions(path: str) -> tuple[int, int]:
    """Return (width, height) without fully decoding the image."""
    try:
        with Image.open(path) as img:
            return img.size  # (width, height)
    except Exception:
        return (0, 0)


def scan(directory: str = config.PHOTOS_DIR) -> list[PhotoEntry]:
    """
    Recursively scan *directory* and return a list of PhotoEntry objects
    sorted by taken_at (oldest first; undated photos go to the end).
    """
    photos: list[PhotoEntry] = []
    base = Path(directory)

    if not base.exists():
        log.warning("Photos directory does not exist: %s", directory)
        return photos

    for ext in SUPPORTED_EXTENSIONS:
        for file_path in base.rglob(f"*{ext}"):
            p = str(file_path)
            taken_at = _read_exif_datetime(p)
            w, h = _read_dimensions(p)
            photos.append(PhotoEntry(path=p, taken_at=taken_at, width=w, height=h))
        # Also match uppercase extensions
        for file_path in base.rglob(f"*{ext.upper()}"):
            p = str(file_path)
            taken_at = _read_exif_datetime(p)
            w, h = _read_dimensions(p)
            photos.append(PhotoEntry(path=p, taken_at=taken_at, width=w, height=h))

    # Deduplicate (rglob on case variants can double-count on case-sensitive fs)
    seen: set[str] = set()
    unique: list[PhotoEntry] = []
    for photo in photos:
        if photo.path not in seen:
            seen.add(photo.path)
            unique.append(photo)

    # Sort: dated photos by timestamp, undated appended at end
    dated   = sorted([p for p in unique if p.taken_at], key=lambda p: p.sort_key)
    undated = [p for p in unique if not p.taken_at]

    log.info("Scanned %d photos (%d dated, %d undated) from %s",
             len(unique), len(dated), len(undated), directory)

    return dated + undated
