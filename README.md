# Photo Frame — Raspberry Pi

Slideshow photo frame application for Raspberry Pi. Supports single-photo slides, collages of time-grouped photos, animated transitions, and auto-reload when the photos directory changes.

---

## Project structure

```
photo-frame/               ← git repo root
├── photo_frame/           ← application source
│   ├── main.py
│   ├── config.py
│   ├── config_test.py     ← overrides used when DOCKER_TEST=1
│   ├── scanner.py
│   ├── scheduler.py
│   ├── layout.py
│   ├── renderer.py
│   └── entry.py           ← console-script entry point
├── docker/
│   └── entrypoint.sh
├── Dockerfile
├── docker-compose.yml
├── install.sh             ← Pi installer
├── pyproject.toml
├── run.sh                 ← Linux/Mac Docker helper
├── run.ps1                ← Windows Docker helper
└── README.md
~/photos/                  ← put your photos here (outside the repo)
```

---

## Local development (Docker)

Docker gives you a fully reproducible environment on any machine — no SDL2 or pygame install needed locally.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / Mac) or Docker Engine (Linux)
- **Windows only (to see the live window):** [VcXsrv](https://sourceforge.net/projects/vcxsrv/) — launch XLaunch, choose *Multiple windows*, display 0, tick *Disable access control*.

### Running

**Windows (PowerShell):**
```powershell
# First run builds the image (~2 min); subsequent runs use the cache.
.\run.ps1                             # windowed — requires VcXsrv
.\run.ps1 -Headless                   # log output only, no window
.\run.ps1 -Photos C:\Users\you\Photos # custom photos folder
.\run.ps1 -Rebuild                    # force image rebuild
.\run.ps1 -Shell                      # drop into a bash shell
```

**Linux / Mac (bash):**
```bash
./run.sh                     # headless by default
./run.sh /path/to/photos     # custom photos folder
./run.sh --rebuild           # force image rebuild
./run.sh --shell             # drop into a bash shell
```

The scripts mount your local photos folder into the container at `/app/photos`. The `DOCKER_TEST=1` environment variable is set automatically, which shrinks the window to 1280×720 and speeds up timing — see [photo_frame/config_test.py](photo_frame/config_test.py).

### Building the image manually

```bash
docker build -t photo-frame-test .
docker run -it --rm -v ./photos:/app/photos:ro -e DOCKER_TEST=1 photo-frame-test
```

---

## Installing on Raspberry Pi OS

### Option A — install script (recommended)

```bash
# Clone the repo then run the installer:
git clone https://github.com/YOUR_USER/photo-frame.git ~/photo-frame
bash ~/photo-frame/install.sh

# To also install and enable a systemd service:
INSTALL_SERVICE=1 bash ~/photo-frame/install.sh
```

The script:
1. Installs `python3-pygame` and SDL2 via `apt` (the most reliable source for Pi OS)
2. Creates a virtual environment at `~/photo-frame/.venv` with `--system-site-packages` so the apt-installed pygame is visible
3. Installs Pillow inside the venv
4. Installs the `photo-frame` package in editable mode, making `photo-frame` available as a command
5. Optionally creates and enables a systemd service

### Option B — pip install (editable)

```bash
sudo apt update
sudo apt install -y python3-venv python3-pygame libsdl2-dev libsdl2-image-dev libjpeg-dev

git clone https://github.com/YOUR_USER/photo-frame.git ~/photo-frame
python3 -m venv --system-site-packages ~/photo-frame/.venv
~/photo-frame/.venv/bin/pip install -e ~/photo-frame

# Run:
~/photo-frame/.venv/bin/photo-frame
```

### Running manually (no venv)

```bash
cd ~/photo-frame/photo_frame
python3 main.py
```

Press **Esc** or **Q** to quit.

---

## LCD setup (SPI displays e.g. ILI9341, ST7789)

For SPI LCDs you need a framebuffer driver so that pygame can write to it.

1. Enable SPI: `sudo raspi-config` → Interface Options → SPI → Enable

2. Install `fbcp-ili9341` (fast framebuffer copy daemon):
   ```bash
   sudo apt install -y cmake
   git clone https://github.com/juj/fbcp-ili9341
   cd fbcp-ili9341 && mkdir build && cd build
   # Adjust flags for your display; example for ILI9341 at 240×320:
   cmake -DILI9341=ON -DGPIO_TFT_DATA_CONTROL=24 -DGPIO_TFT_RESET_PIN=25 \
         -DSPI_BUS_CLOCK_DIVISOR=6 -DBACKLIGHT_CONTROL=ON \
         -DGPIO_TFT_BACKLIGHT=18 ..
   make -j
   sudo ./fbcp-ili9341 &
   ```
   This copies `/dev/fb0` (pygame output) to the LCD in real time.

3. Tell pygame to use the framebuffer — add to the top of `photo_frame/main.py` **before** `import pygame`:
   ```python
   import os
   os.environ["SDL_VIDEODRIVER"] = "fbcon"
   os.environ["SDL_FBDEV"]       = "/dev/fb0"
   ```
   Or set these in the systemd service (the install script does this automatically).

---

## Auto-start on boot (systemd)

The `INSTALL_SERVICE=1` flag in `install.sh` handles this. To set it up manually:

```ini
# /etc/systemd/system/photo-frame.service
[Unit]
Description=Photo Frame
After=multi-user.target

[Service]
User=pi
WorkingDirectory=/home/pi/photo-frame/photo_frame
Environment="SDL_VIDEODRIVER=fbcon"
Environment="SDL_FBDEV=/dev/fb0"
ExecStart=/home/pi/photo-frame/.venv/bin/python3 /home/pi/photo-frame/photo_frame/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable photo-frame
sudo systemctl start photo-frame
```

---

## Configuration quick-reference

Edit [photo_frame/config.py](photo_frame/config.py) to adjust settings:

| Variable | Default | Description |
|---|---|---|
| `SCREEN_WIDTH/HEIGHT` | 1920×1080 | Match your display |
| `FULLSCREEN` | `True` | Set `False` for windowed testing |
| `PHOTOS_DIR` | `~/photos` | Where photos are read from |
| `DISPLAY_SECS` | 15 | Seconds per slide |
| `TRANSITION_SECS` | 0.6 | Slide animation duration |
| `TRANSITION_TYPE` | `"slide"` | `slide` / `fade` / `cut` |
| `SLIDE_DIRECTION` | `"random"` | `left` / `right` / `up` / `down` / `random` |
| `GROUP_WINDOW_MINS` | 30 | Time window for grouping photos into collages |
| `FIT_THRESHOLD` | 0.60 | Below this aspect-ratio score → try collage |
| `HISTORY_SIZE` | 50 | Recent photos to remember (avoids repeats) |
| `RELOAD_CHECK_SECS` | 30 | Auto-reload check interval |
| `FPS` | 60 | Render frame rate |
