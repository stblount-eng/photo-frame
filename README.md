# Photo Frame — Raspberry Pi Zero 2

## Requirements

```
pygame==2.6.1
Pillow==10.4.0
```

Install on the Pi:

```bash
sudo apt update
sudo apt install -y python3-pip python3-pygame libsdl2-dev libsdl2-image-dev
pip3 install Pillow --break-system-packages
# pygame is best installed via apt on Pi OS:
sudo apt install -y python3-pygame
```

---

## Directory layout

```
~/photo_frame/
├── main.py
├── config.py
├── scanner.py
├── scheduler.py
├── layout.py
├── renderer.py
~/photos/           ← put your photos here (subfolders supported)
```

---

## Running

```bash
cd ~/photo_frame
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
   # Adjust flags for your exact display; example for common 240×320 ILI9341:
   cmake -DILI9341=ON -DGPIO_TFT_DATA_CONTROL=24 -DGPIO_TFT_RESET_PIN=25 \
         -DSPI_BUS_CLOCK_DIVISOR=6 -DBACKLIGHT_CONTROL=ON \
         -DGPIO_TFT_BACKLIGHT=18 ..
   make -j
   sudo ./fbcp-ili9341 &
   ```
   This copies `/dev/fb0` (pygame output) to your LCD in real time.

3. Tell pygame to use the framebuffer instead of X:
   Add to the top of `main.py` **before** `import pygame`:
   ```python
   import os
   os.environ["SDL_VIDEODRIVER"] = "fbcon"
   os.environ["SDL_FBDEV"]       = "/dev/fb0"
   ```
   Or export these in your shell / systemd service file.

---

## Auto-start on boot (systemd)

```ini
# /etc/systemd/system/photoframe.service
[Unit]
Description=Photo Frame
After=multi-user.target

[Service]
User=pi
WorkingDirectory=/home/pi/photo_frame
Environment="SDL_VIDEODRIVER=fbcon"
Environment="SDL_FBDEV=/dev/fb0"
ExecStart=/usr/bin/python3 /home/pi/photo_frame/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable photoframe
sudo systemctl start photoframe
```

---

## Configuration quick-reference

| Variable | Default | Description |
|---|---|---|
| `SCREEN_WIDTH/HEIGHT` | 1920×1080 | Match your LCD |
| `DISPLAY_SECS` | 15 | Seconds per slide |
| `TRANSITION_SECS` | 0.6 | Slide animation duration |
| `GROUP_WINDOW_MINS` | 30 | Time window for grouping photos |
| `FIT_THRESHOLD` | 0.60 | Below this → try collage |
| `HISTORY_SIZE` | 50 | Recents to remember |
| `RELOAD_CHECK_SECS` | 30 | Auto-reload check interval |
| `SLIDE_DIRECTION` | "random" | left/right/up/down/random |
