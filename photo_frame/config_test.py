"""
config_test.py — overrides for local Docker testing.

Loaded automatically when the DOCKER_TEST=1 env var is set.
Keeps display small and timing fast so you can iterate quickly.
"""

SCREEN_WIDTH   = 1280
SCREEN_HEIGHT  = 720
FULLSCREEN     = False    # Windowed so Xvfb can render it

DISPLAY_SECS   = 5        # Faster cycling during testing
TRANSITION_SECS = 0.4

RELOAD_CHECK_SECS = 5     # Quicker reload checks
