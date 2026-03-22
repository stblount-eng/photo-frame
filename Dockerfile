FROM python:3.12-slim

# System deps: SDL2 for pygame, Xvfb for virtual display, x11-utils for debugging
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11-utils \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libgl1 \
    libglib2.0-0 \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libtiff-dev \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pygame==2.6.1 Pillow==10.4.0

WORKDIR /app

# Copy application source
COPY photo_frame/ ./

# Copy sample photos if present (optional — container works without them)
# The run script mounts your local photos dir at /app/photos at runtime

# Virtual display dimensions — match your test window size (not necessarily 1920x1080)
ENV DISPLAY=:99
ENV SDL_VIDEODRIVER=x11

# Xvfb screen index 0: 1280x720 24-bit colour — good enough for testing
ENV XVFB_SCREEN=0
ENV XVFB_RES=1280x720x24

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
