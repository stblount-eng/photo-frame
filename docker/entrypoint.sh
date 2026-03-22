#!/bin/bash
set -e

if [ -n "$DISPLAY_HOST" ]; then
    # --- Windowed mode: forward to Windows X server (VcXsrv) ---
    export DISPLAY="${DISPLAY_HOST}:0.0"
    export SDL_VIDEODRIVER=x11
    echo "▶  Using X11 display forwarded to ${DISPLAY_HOST}"
else
    # --- Headless mode: virtual Xvfb display (logs only, no window) ---
    export DISPLAY=:99
    export SDL_VIDEODRIVER=x11
    echo "▶  Starting virtual display (Xvfb :99 ${XVFB_RES:-1280x720x24})..."
    Xvfb :99 -screen 0 "${XVFB_RES:-1280x720x24}" -ac +extension GLX +render -noreset &

    for i in $(seq 1 20); do
        if xdpyinfo -display :99 >/dev/null 2>&1; then
            echo "✔  Virtual display ready."
            break
        fi
        sleep 0.2
    done
fi

# Suppress ALSA errors — no sound card in container, audio not needed
export SDL_AUDIODRIVER=dummy

echo "▶  Launching photo frame..."
exec python3 main.py "$@"
