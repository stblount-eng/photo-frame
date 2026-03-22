#!/usr/bin/env bash
# install.sh — Install photo-frame on Raspberry Pi OS (Bullseye or Bookworm).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_USER/photo-frame/main/install.sh | bash
#   # — or, after cloning the repo —
#   bash install.sh
#
# Options (environment variables):
#   INSTALL_DIR   Where to clone/use the repo  (default: ~/photo-frame)
#   PHOTOS_DIR    Where photos are read from    (default: ~/photos)
#   INSTALL_SERVICE=1  Also install & enable a systemd service (default: 0)

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/photo-frame}"
PHOTOS_DIR="${PHOTOS_DIR:-$HOME/photos}"
INSTALL_SERVICE="${INSTALL_SERVICE:-0}"
VENV_DIR="$INSTALL_DIR/.venv"

echo "┌─────────────────────────────────────────────┐"
echo "│     Photo Frame — Raspberry Pi Installer    │"
echo "└─────────────────────────────────────────────┘"
echo "  Install dir : $INSTALL_DIR"
echo "  Photos dir  : $PHOTOS_DIR"
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo "▶  Installing system dependencies via apt..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-pygame \
    libsdl2-dev \
    libsdl2-image-dev \
    libjpeg-dev \
    libpng-dev \
    git
echo "✔  System packages installed."
echo ""

# ── 2. Clone or update the repo ───────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "▶  Updating existing repo at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    # If running from inside the repo already, just note the path
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
        echo "▶  Using existing repo at $SCRIPT_DIR"
        INSTALL_DIR="$SCRIPT_DIR"
    else
        echo "▶  Cloning repo to $INSTALL_DIR..."
        git clone https://github.com/YOUR_USER/photo-frame.git "$INSTALL_DIR"
    fi
fi
VENV_DIR="$INSTALL_DIR/.venv"
echo ""

# ── 3. Create virtual environment (with access to system pygame) ──────────────
echo "▶  Creating Python virtual environment at $VENV_DIR..."
python3 -m venv --system-site-packages "$VENV_DIR"
echo "✔  Virtual environment ready."
echo ""

# ── 4. Install Python dependencies ───────────────────────────────────────────
echo "▶  Installing Python dependencies (Pillow)..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet Pillow
echo "✔  Python dependencies installed."
echo ""

# ── 5. Install the package itself (editable) ─────────────────────────────────
echo "▶  Installing photo-frame package..."
"$VENV_DIR/bin/pip" install --quiet -e "$INSTALL_DIR"
echo "✔  photo-frame installed. Run with: $VENV_DIR/bin/photo-frame"
echo ""

# ── 6. Create photos directory ───────────────────────────────────────────────
mkdir -p "$PHOTOS_DIR"
echo "✔  Photos directory: $PHOTOS_DIR"
echo ""

# ── 7. Optionally install systemd service ────────────────────────────────────
if [ "$INSTALL_SERVICE" = "1" ]; then
    echo "▶  Installing systemd service..."

    SERVICE_FILE="/etc/systemd/system/photo-frame.service"
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Photo Frame
After=multi-user.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR/photo_frame
Environment="SDL_VIDEODRIVER=fbcon"
Environment="SDL_FBDEV=/dev/fb0"
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/photo_frame/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable photo-frame
    sudo systemctl start photo-frame
    echo "✔  Service installed and started."
    echo "   sudo systemctl status photo-frame"
else
    echo "──────────────────────────────────────────────"
    echo "  To run manually:"
    echo "    $VENV_DIR/bin/photo-frame"
    echo "  Or:"
    echo "    cd $INSTALL_DIR/photo_frame && python3 main.py"
    echo ""
    echo "  To also install a systemd service, re-run with:"
    echo "    INSTALL_SERVICE=1 bash $INSTALL_DIR/install.sh"
    echo "──────────────────────────────────────────────"
fi
echo ""
echo "✔  Done! Put your photos in: $PHOTOS_DIR"
