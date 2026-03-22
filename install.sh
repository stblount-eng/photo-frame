#!/usr/bin/env bash
# install.sh — Install photo-frame on Raspberry Pi OS (Bullseye or Bookworm).
#
# Usage:
#   bash install.sh
#
# Options (environment variables):
#   INSTALL_DIR     Where to clone/use the repo  (default: ~/photo-frame)
#   PHOTOS_DIR      Where photos are read from    (default: ~/photos)
#   INSTALL_SERVICE=1  Install & enable systemd auto-start (default: 1)
#   INSTALL_SAMBA=1    Install & configure Samba network share (default: 1)

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-$HOME/photo-frame}"
PHOTOS_DIR="${PHOTOS_DIR:-$HOME/photos}"
INSTALL_SERVICE="${INSTALL_SERVICE:-1}"
INSTALL_SAMBA="${INSTALL_SAMBA:-1}"
VENV_DIR="$INSTALL_DIR/.venv"

echo "================================================"
echo "  Photo Frame - Raspberry Pi Installer"
echo "================================================"
echo "  Install dir  : $INSTALL_DIR"
echo "  Photos dir   : $PHOTOS_DIR"
echo "  Systemd      : $INSTALL_SERVICE"
echo "  Samba share  : $INSTALL_SAMBA"
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo ">> Installing system dependencies via apt..."
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
echo "   Done."
echo ""

# ── 2. Clone or update the repo ───────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo ">> Updating existing repo at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
        echo ">> Using existing repo at $SCRIPT_DIR"
        INSTALL_DIR="$SCRIPT_DIR"
    else
        echo ">> Cloning repo to $INSTALL_DIR..."
        git clone https://github.com/YOUR_USER/photo-frame.git "$INSTALL_DIR"
    fi
fi
VENV_DIR="$INSTALL_DIR/.venv"
echo ""

# ── 3. Create virtual environment ─────────────────────────────────────────────
echo ">> Creating Python virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"
echo ""

# ── 4. Install Python dependencies ───────────────────────────────────────────
echo ">> Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet Pillow
echo ""

# ── 5. Install the package (editable) ────────────────────────────────────────
echo ">> Installing photo-frame package..."
"$VENV_DIR/bin/pip" install --quiet -e "$INSTALL_DIR"
echo ""

# ── 6. Create photos directory ───────────────────────────────────────────────
mkdir -p "$PHOTOS_DIR"
echo ">> Photos directory: $PHOTOS_DIR"
echo ""

# ── 7. Systemd service ───────────────────────────────────────────────────────
if [ "$INSTALL_SERVICE" = "1" ]; then
    echo ">> Installing systemd service (photo-frame)..."

    # Ensure the user can access the framebuffer device
    sudo usermod -a -G video "$USER"

    sudo tee /etc/systemd/system/photo-frame.service > /dev/null <<UNIT
[Unit]
Description=Photo Frame
After=multi-user.target

[Service]
User=$USER
SupplementaryGroups=video
WorkingDirectory=$INSTALL_DIR/photo_frame
Environment="SDL_VIDEODRIVER=fbcon"
Environment="SDL_FBDEV=/dev/fb0"
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/photo_frame/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

    sudo systemctl daemon-reload
    sudo systemctl enable photo-frame
    sudo systemctl start photo-frame
    echo "   Enabled and started. Check: sudo systemctl status photo-frame"
    echo ""
fi

# ── 8. Samba network share ───────────────────────────────────────────────────
if [ "$INSTALL_SAMBA" = "1" ]; then
    echo ">> Installing Samba (will retry up to 3 times on mirror failures)..."
    for attempt in 1 2 3; do
        sudo apt-get install -y --no-install-recommends samba && break
        if [ "$attempt" -eq 3 ]; then
            echo "ERROR: Samba installation failed after 3 attempts."
            echo "  Try manually: sudo apt-get update && sudo apt-get install -y samba"
            exit 1
        fi
        echo "   Attempt $attempt failed, retrying after apt-get update..."
        sudo apt-get update -qq
    done
    echo ""

    SHARE_NAME="photos"

    # Disable SMB1 in the [global] section if not already set
    if ! grep -q "min protocol" /etc/samba/smb.conf; then
        echo ">> Disabling SMB1 (setting min protocol = SMB2)..."
        sudo sed -i '/^\[global\]/a\   min protocol = SMB2' /etc/samba/smb.conf
    fi

    # Only append the share block if it isn't already in smb.conf
    if ! grep -q "^\[$SHARE_NAME\]" /etc/samba/smb.conf; then
        echo ">> Adding [$SHARE_NAME] share to /etc/samba/smb.conf..."
        sudo tee -a /etc/samba/smb.conf > /dev/null <<SAMBA

[$SHARE_NAME]
   comment = Photo Frame Photos
   path = $PHOTOS_DIR
   browseable = yes
   writable = yes
   create mask = 0644
   directory mask = 0755
   valid users = $USER
   force user = $USER
SAMBA
    else
        echo ">> Samba share [$SHARE_NAME] already configured — skipping."
    fi

    echo ""
    echo ">> Set the Samba password for user '$USER':"
    echo "   (This is the password you will use from Windows/Mac to connect)"
    sudo smbpasswd -a "$USER"

    sudo systemctl enable smbd nmbd
    sudo systemctl restart smbd nmbd
    echo ""

    # Determine Pi's IP for connection instructions
    PI_IP=$(hostname -I | awk '{print $1}')
    echo "================================================"
    echo "  Samba share ready."
    echo ""
    echo "  From Windows:  \\${PI_IP}\photos"
    echo "                 or \\$(hostname)\photos"
    echo "  From Mac:      smb://${PI_IP}/photos"
    echo "  From Linux:    smb://${PI_IP}/photos"
    echo ""
    echo "  Drop photos into this share and the slideshow"
    echo "  will pick them up within 30 seconds."
    echo "================================================"
    echo ""
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo "================================================"
echo "  Installation complete!"
echo ""
if [ "$INSTALL_SERVICE" != "1" ]; then
    echo "  Run manually:"
    echo "    $VENV_DIR/bin/photo-frame"
    echo "  Or enable auto-start:"
    echo "    INSTALL_SERVICE=1 bash $INSTALL_DIR/install.sh"
    echo ""
fi
if [ "$INSTALL_SAMBA" != "1" ]; then
    echo "  Enable network photo share:"
    echo "    INSTALL_SAMBA=1 bash $INSTALL_DIR/install.sh"
    echo ""
fi
echo "  Photos directory: $PHOTOS_DIR"
echo "================================================"
