"""
Photo Frame Configuration
Adjust these values to match your setup.
"""
import os

# --- Display ---
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1080
FULLSCREEN    = True          # Set False for windowed testing on a desktop

# --- Paths ---
PHOTOS_DIR         = os.path.expanduser("~/photos")   # Put your photos here
HISTORY_FILE       = os.path.expanduser("~/.photo_frame_history.json")

# --- Slideshow timing ---
DISPLAY_SECS       = 15       # Seconds each slide is shown
TRANSITION_SECS    = 0.6      # Duration of slide-in transition

# --- Duplicate avoidance ---
HISTORY_SIZE       = 50       # Remember this many recent photos; won't repeat them

# --- Photo grouping (collage) ---
GROUP_WINDOW_MINS  = 30       # Photos within this window can be grouped together
FIT_THRESHOLD      = 0.60     # Aspect-ratio fit score below this → try grouping
                               # Score = min(photo_ar, screen_ar) / max(photo_ar, screen_ar)
COLLAGE_GAP        = 6        # Pixels between photos in a collage
COLLAGE_BG         = (15, 15, 15)  # Background colour (R, G, B)

# --- Transitions ---
TRANSITION_TYPE    = "slide"  # "slide" | "fade" | "cut"
SLIDE_DIRECTION    = "random" # "left" | "right" | "up" | "down" | "random"

# --- Auto-reload ---
RELOAD_CHECK_SECS  = 30       # How often to check for new/removed photos

# --- Display ---
FPS                = 60
FONT_PATH          = None     # None = use pygame default; or path to a .ttf

# ---------------------------------------------------------------------------
# Test overrides — applied automatically when DOCKER_TEST=1
# ---------------------------------------------------------------------------
import os as _os
if _os.environ.get("DOCKER_TEST") == "1":
    try:
        from config_test import *  # noqa: F401,F403
    except ImportError:
        pass
