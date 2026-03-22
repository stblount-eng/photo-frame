"""
main.py — Photo Frame entry point.

Wires together: scanner → scheduler → layout → renderer
with optional auto-reload when photos directory changes.
"""
import logging
import os
import sys
import time
import threading
from pathlib import Path

import config
import scanner
import scheduler as sched_mod
import layout
import renderer as rend_mod

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Auto-reload watcher
# ---------------------------------------------------------------------------

class PhotoWatcher(threading.Thread):
    """
    Background thread that periodically checks whether the photos
    directory has changed (using the directory's mtime + total file count).
    Calls *callback* when a change is detected.
    """
    def __init__(self, callback):
        super().__init__(daemon=True)
        self._callback  = callback
        self._stop_evt  = threading.Event()
        self._last_sig  = self._signature()

    def _signature(self) -> tuple:
        base = Path(config.PHOTOS_DIR)
        if not base.exists():
            return (0, 0)
        files = list(base.rglob("*"))
        return (len(files), max((f.stat().st_mtime for f in files if f.is_file()), default=0))

    def run(self):
        while not self._stop_evt.wait(config.RELOAD_CHECK_SECS):
            sig = self._signature()
            if sig != self._last_sig:
                log.info("Photo directory changed — reloading.")
                self._last_sig = sig
                try:
                    self._callback()
                except Exception as e:
                    log.error("Reload callback error: %s", e)

    def stop(self):
        self._stop_evt.set()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Ensure photos directory exists
    os.makedirs(config.PHOTOS_DIR, exist_ok=True)

    # Initial scan
    log.info("Scanning photos in %s …", config.PHOTOS_DIR)
    photos = scanner.scan()
    if not photos:
        log.warning("No photos found in %s. Add photos and restart (or wait for auto-reload).",
                    config.PHOTOS_DIR)

    # Build scheduler and renderer
    schedule  = sched_mod.Scheduler(photos)
    renderer  = rend_mod.Renderer()

    # Auto-reload callback
    def reload_photos():
        new_photos = scanner.scan()
        schedule.update_photos(new_photos)

    watcher = PhotoWatcher(callback=reload_photos)
    watcher.start()

    # Pre-render the first slide off the bat so there's no black flash
    current_surface = None
    next_surface    = None

    def prepare_next() -> "pygame.Surface | None":
        slide = schedule.next_slide()
        if slide is None:
            return None
        log.info("Preparing slide: %s", [p.path for p in slide])
        return layout.render_slide(slide)

    # Pre-load first two slides
    next_surface = prepare_next()
    # Start background pre-loading thread
    preload_surface = [None]
    preload_lock    = threading.Lock()

    def preload_worker():
        surf = prepare_next()
        with preload_lock:
            preload_surface[0] = surf

    preload_thread = threading.Thread(target=preload_worker, daemon=True)
    preload_thread.start()

    running       = True
    display_until = time.monotonic()   # show immediately on first iteration

    try:
        while running:
            now = time.monotonic()

            # Time to show the next slide?
            if now >= display_until:
                if next_surface is not None:
                    renderer.show(next_surface)
                    current_surface = next_surface

                display_until = time.monotonic() + config.DISPLAY_SECS

                # Grab pre-loaded surface (or prepare synchronously if not ready)
                with preload_lock:
                    next_surface       = preload_surface[0]
                    preload_surface[0] = None

                if next_surface is None:
                    next_surface = prepare_next()

                # Kick off next pre-load
                if not preload_thread.is_alive():
                    preload_thread = threading.Thread(target=preload_worker, daemon=True)
                    preload_thread.start()

            # Handle input
            running = renderer.pump_events()

            renderer.clock.tick(config.FPS)

    except KeyboardInterrupt:
        log.info("Interrupted — shutting down.")
    finally:
        watcher.stop()
        renderer.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()
