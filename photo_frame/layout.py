"""
layout.py — Compute screen rectangles for single and collage slides.

Returns a list of (PhotoEntry, pygame.Rect) pairs describing where
each photo should be drawn on screen.
"""
import logging
from typing import NamedTuple

import pygame

from scanner import PhotoEntry
from scheduler import _best_collage_grid
import config

log = logging.getLogger(__name__)


class PlacedPhoto(NamedTuple):
    photo: PhotoEntry
    dest: pygame.Rect   # Where on screen to draw it


def _fit_rect(photo_w: int, photo_h: int, cell: pygame.Rect) -> pygame.Rect:
    """
    Scale the photo to fill the cell while maintaining aspect ratio (cover),
    then centre it.  Returns the source crop rect in photo coordinates.
    This gives a "fill" behaviour — no black bars.
    """
    if photo_w == 0 or photo_h == 0:
        return cell

    scale_x = cell.width  / photo_w
    scale_y = cell.height / photo_h
    scale   = max(scale_x, scale_y)   # cover

    scaled_w = int(photo_w * scale)
    scaled_h = int(photo_h * scale)

    # Centre crop
    x = (scaled_w - cell.width)  // 2
    y = (scaled_h - cell.height) // 2
    return pygame.Rect(x, y, cell.width, cell.height)


def compute_layout(slide: list[PhotoEntry]) -> list[PlacedPhoto]:
    """
    Given 1–4 photos, return their screen placements.
    Each PlacedPhoto.dest is the destination rect on the full screen.
    """
    sw, sh = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
    gap    = config.COLLAGE_GAP
    n      = len(slide)

    if n == 1:
        return [PlacedPhoto(photo=slide[0], dest=pygame.Rect(0, 0, sw, sh))]

    cols, rows = _best_collage_grid(n)

    cell_w = (sw - gap * (cols - 1)) // cols
    cell_h = (sh - gap * (rows - 1)) // rows

    placements: list[PlacedPhoto] = []
    for i, photo in enumerate(slide[:cols * rows]):
        col = i % cols
        row = i // cols
        x   = col * (cell_w + gap)
        y   = row * (cell_h + gap)
        dest = pygame.Rect(x, y, cell_w, cell_h)
        placements.append(PlacedPhoto(photo=photo, dest=dest))

    return placements


def render_slide(
    slide: list[PhotoEntry],
    screen_size: tuple[int, int] = (config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
) -> pygame.Surface:
    """
    Load and composite all photos in a slide onto a single Surface
    the size of the screen.  This is done off-screen and returned
    ready to blit.
    """
    surface = pygame.Surface(screen_size)
    surface.fill(config.COLLAGE_BG)

    placements = compute_layout(slide)

    for placed in placements:
        try:
            img = pygame.image.load(placed.photo.path).convert()
        except Exception as e:
            log.warning("Could not load image %s: %s", placed.photo.path, e)
            continue

        dest  = placed.dest
        img_w, img_h = img.get_size()

        # Scale to cover the cell
        scale_x = dest.width  / img_w
        scale_y = dest.height / img_h
        scale   = max(scale_x, scale_y)
        new_w   = int(img_w * scale)
        new_h   = int(img_h * scale)

        scaled = pygame.transform.smoothscale(img, (new_w, new_h))

        # Crop to cell size from centre
        crop_x = (new_w - dest.width)  // 2
        crop_y = (new_h - dest.height) // 2
        crop_rect = pygame.Rect(crop_x, crop_y, dest.width, dest.height)

        surface.blit(scaled, dest.topleft, crop_rect)

    return surface
