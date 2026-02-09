# Nabaixin TFOLED

A HAT breakout board driver for Raspberry Pi, including RTC (Real-Time Clock), Fan control, and OLED display (SSD1306 128×32).

[中文说明](https://www.jianshu.com/p/0bcf3dde7048)

![IMG2940.JPG](https://upload-images.jianshu.io/upload_images/24088362-3d77a28a670af95d.JPG?imageMogr2/auto-orient/strip|imageView2/2/w/1200/format/webp)

## Features

- 🖥️ SSD1306 OLED display (128×32, I2C) — shows IP, CPU, memory, disk, temperature
- 🌡️ Automatic fan control based on CPU temperature
- ⏰ RTC support via DS1307/DS3231 (kernel driver)

## Supported Platforms

| Raspberry Pi | OS | Status |
|---|---|---|
| Pi 2B / 3B / 3B+ | Raspberry Pi OS / Ubuntu | ✅ |
| Pi 4B / Pi 400 | Raspberry Pi OS / Ubuntu | ✅ |
| Pi 5 | Raspberry Pi OS / Ubuntu | ✅ |

## Requirements

- Python >= 3.7
- I2C enabled:
  - `sudo raspi-config` → Interface Options → I2C → Enable
  - Or manually add `dtparam=i2c_arm=on` to `/boot/config.txt` (`/boot/firmware/config.txt`)
- RTC (DS1307) enabled:
  - Manually add `dtoverlay=i2c-rtc,ds1307` to `/boot/config.txt` (`/boot/firmware/config.txt`)

## Installation

### Using pip

```bash
pip install -r requirements.txt
pip install .
```

### Using uv

```bash
uv pip install .
```

### GPIO dependency

The fan control requires a GPIO library. Choose based on your OS:

| OS | GPIO library | Install command |
|---|---|---|
| **Raspberry Pi OS (Pi 1-4)** | RPi.GPIO (pre-installed) | Nothing to do |
| **Raspberry Pi OS (Pi 5)** | rpi-lgpio (pre-installed) | Nothing to do |
| **Ubuntu / Debian** | rpi-lgpio | `pip install rpi-lgpio` |

Or using optional dependency groups:

```bash
# Ubuntu / Debian
pip install ".[gpio-modern]"

# Raspberry Pi OS (if RPi.GPIO is somehow missing)
pip install ".[gpio-legacy]"
```

> ⚠️ `rpi-lgpio` and `RPi.GPIO` cannot be installed at the same time. Choose one.

## Usage

```bash
python3 TFOL.py
```

The OLED display will show:
```
2026-02-09 14:30:00
IP: 192.168.1.100
CPU:0.52 CT:45
Mem:512/1024M  D:8/32G
```

The fan (GPIO 4) automatically turns on when CPU temperature > 60°C and off when < 45°C.

## Project Structure

```
NBX_OLED/          # SSD1306 OLED driver library (smbus2-based)
  ├── __init__.py
  └── OLED.py
TFOL.py            # Main application (system monitor display + fan control)
pyproject.toml     # Project metadata & dependencies
requirements.txt   # Dependency list (pip)
setup.py           # Backward compatibility shim
tool/              # Utilities (SSH, WiFi config)
```

## License

MIT

## Links

- GitHub: [https://github.com/nabaixin/TFOLED/](https://github.com/nabaixin/TFOLED/)
- 淘宝店：[https://keliu.taobao.com/](https://keliu.taobao.com/)
