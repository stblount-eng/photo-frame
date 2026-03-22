"""
scheduler.py — Slide selection with grouping and duplicate avoidance.

Given a list of PhotoEntry objects, the scheduler picks the next
"slide" which is either:
  - A single photo (good aspect-ratio fit), or
  - A list of 2–4 photos taken close together in time (collage).

History of recently shown photos is persisted to disk so it survives
restarts.
"""
import json
import logging
import random
from collections import deque
from datetime import timedelta
from pathlib import Path
from typing import Optional

from scanner import PhotoEntry
import config

log = logging.getLogger(__name__)


class History:
    """Persist a fixed-size deque of recently shown photo paths."""

    def __init__(self, path: str = config.HISTORY_FILE, maxlen: int = config.HISTORY_SIZE):
        self._path = Path(path)
        self._maxlen = maxlen
        self._deque: deque[str] = deque(maxlen=maxlen)
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text())
                self._deque = deque(data.get("history", []), maxlen=self._maxlen)
        except Exception as e:
            log.warning("Could not load history: %s", e)

    def save(self):
        try:
            self._path.write_text(json.dumps({"history": list(self._deque)}, indent=2))
        except Exception as e:
            log.warning("Could not save history: %s", e)

    def add(self, paths: list[str]):
        for p in paths:
            self._deque.append(p)

    def seen_recently(self, path: str) -> bool:
        return path in self._deque

    def clear(self):
        self._deque.clear()
        self.save()


def _time_cluster(photo: PhotoEntry, all_photos: list[PhotoEntry]) -> list[PhotoEntry]:
    """
    Return photos taken within GROUP_WINDOW_MINS of *photo* (including itself).
    Returns [photo] if it has no taken_at.
    """
    if not photo.taken_at:
        return [photo]

    window = timedelta(minutes=config.GROUP_WINDOW_MINS)
    cluster = [
        p for p in all_photos
        if p.taken_at and abs(p.taken_at - photo.taken_at) <= window
    ]
    return cluster if cluster else [photo]


def _best_collage_grid(n: int) -> tuple[int, int]:
    """
    Given n photos, return (cols, rows) for the best-filling grid.
    Caps at 4 photos (2×2).
    """
    layouts = {
        2: (2, 1),   # side by side
        3: (3, 1),   # three in a row  (or could be 2+1 but keep simple)
        4: (2, 2),
    }
    return layouts.get(min(n, 4), (1, 1))


class Scheduler:
    def __init__(self, photos: list[PhotoEntry]):
        self.photos = photos
        self.history = History()

    def update_photos(self, photos: list[PhotoEntry]):
        """Hot-swap the photo list (called on auto-reload)."""
        self.photos = photos
        log.info("Scheduler updated: %d photos available", len(photos))

    def next_slide(self) -> Optional[list[PhotoEntry]]:
        """
        Return the next slide as a list of PhotoEntry objects.
        Single photo  → list of length 1.
        Collage        → list of 2–4 photos.
        Returns None if no photos are available.
        """
        if not self.photos:
            return None

        # Build pool excluding recently seen photos
        pool = [p for p in self.photos if not self.history.seen_recently(p.path)]
        if not pool:
            # All photos seen — reset history and start fresh
            log.info("All photos shown recently; resetting history.")
            self.history.clear()
            pool = list(self.photos)

        # Pick a random candidate
        candidate = random.choice(pool)

        # Decide: single or collage?
        if candidate.fit_score >= config.FIT_THRESHOLD:
            slide = [candidate]
        else:
            cluster = _time_cluster(candidate, self.photos)
            # Remove the candidate itself to pick companions
            companions = [p for p in cluster if p.path != candidate.path
                          and not self.history.seen_recently(p.path)]

            if not companions:
                # No nearby unseen photos — just show the single
                slide = [candidate]
            else:
                # Pick enough companions for a nice grid (up to 3 companions = 4 total)
                n_companions = min(len(companions), 3)
                chosen = random.sample(companions, n_companions)
                slide = [candidate] + chosen
                # Shuffle order so the anchor isn't always top-left
                random.shuffle(slide)

        paths = [p.path for p in slide]
        self.history.add(paths)
        self.history.save()
        log.debug("Next slide: %s", paths)
        return slide
