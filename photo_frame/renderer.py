"""
renderer.py — Pygame display, slide transitions, and the render loop.

Supports:
  - "slide"  — new slide slides in from a random edge
  - "fade"   — cross-fade between slides
  - "cut"    — instant replacement
"""
import logging
import random
import time

import pygame

import config

log = logging.getLogger(__name__)

Direction = str   # "left" | "right" | "up" | "down"
DIRECTIONS: list[Direction] = ["left", "right", "up", "down"]


def _pick_direction() -> Direction:
    if config.SLIDE_DIRECTION == "random":
        return random.choice(DIRECTIONS)
    return config.SLIDE_DIRECTION


class Renderer:
    def __init__(self):
        pygame.init()

        if not pygame.display.get_init():
            raise RuntimeError(
                "pygame could not initialise the display.\n"
                "  • Raspberry Pi (fbcon): make sure the service user is in the 'video' group:\n"
                "      sudo usermod -a -G video $USER\n"
                "    and that the service has SupplementaryGroups=video in its unit file.\n"
                "  • Docker/headless: make sure DISPLAY is set and Xvfb is running.\n"
                "  • Windows windowed mode: start VcXsrv with 'Disable access control' ticked,\n"
                "    then re-run with -e DISPLAY_HOST=host.docker.internal."
            )

        pygame.display.set_caption("Photo Frame")
        flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF if config.FULLSCREEN else 0
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags
        )
        pygame.mouse.set_visible(False)
        self.clock   = pygame.time.Clock()
        self.current: pygame.Surface | None = None

        # Black start
        self.screen.fill((0, 0, 0))
        pygame.display.flip()

    def show(self, new_surface: pygame.Surface):
        """
        Transition from the current surface to *new_surface* using the
        configured transition type, then hold until DISPLAY_SECS elapses.
        """
        if self.current is None:
            # First slide — just show it
            self.screen.blit(new_surface, (0, 0))
            pygame.display.flip()
            self.current = new_surface
            return

        t = config.TRANSITION_TYPE
        if t == "slide":
            self._transition_slide(new_surface)
        elif t == "fade":
            self._transition_fade(new_surface)
        else:
            self.screen.blit(new_surface, (0, 0))
            pygame.display.flip()

        self.current = new_surface

    def _transition_slide(self, new_surface: pygame.Surface):
        direction = _pick_direction()
        sw, sh = config.SCREEN_WIDTH, config.SCREEN_HEIGHT
        duration = config.TRANSITION_SECS
        fps      = config.FPS

        steps = max(1, int(duration * fps))

        for step in range(steps + 1):
            t = step / steps  # 0.0 → 1.0
            # Ease in-out cubic
            if t < 0.5:
                ease = 4 * t * t * t
            else:
                ease = 1 - (-2 * t + 2) ** 3 / 2

            if direction == "left":
                # new comes from right
                old_x = int(-sw * ease)
                new_x = int(sw  * (1 - ease))
                old_y = new_y = 0
            elif direction == "right":
                old_x = int(sw * ease)
                new_x = int(-sw * (1 - ease))
                old_y = new_y = 0
            elif direction == "up":
                old_x = new_x = 0
                old_y = int(-sh * ease)
                new_y = int(sh  * (1 - ease))
            else:  # down
                old_x = new_x = 0
                old_y = int(sh * ease)
                new_y = int(-sh * (1 - ease))

            self.screen.fill((0, 0, 0))
            self.screen.blit(self.current, (old_x, old_y))
            self.screen.blit(new_surface,  (new_x, new_y))
            pygame.display.flip()
            self.clock.tick(fps)

    def _transition_fade(self, new_surface: pygame.Surface):
        duration = config.TRANSITION_SECS
        fps      = config.FPS
        steps    = max(1, int(duration * fps))
        overlay  = new_surface.copy()

        for step in range(steps + 1):
            alpha = int(255 * (step / steps))
            overlay.set_alpha(alpha)
            self.screen.blit(self.current, (0, 0))
            self.screen.blit(overlay, (0, 0))
            pygame.display.flip()
            self.clock.tick(fps)

    def pump_events(self) -> bool:
        """
        Process pygame events.
        Returns False if the user requests quit (Esc / window close).
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
        return True

    def quit(self):
        pygame.quit()
