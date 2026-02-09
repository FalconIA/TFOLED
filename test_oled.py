#!/usr/bin/env python3
"""
OLED Diagnostic Test Script
============================
Step-by-step tests for SSD1306 OLED: I2C comm, pixel output, etc.
Helps determine whether the OLED is burned out.

Usage:
    sudo python3 test_oled.py
    sudo python3 test_oled.py --bus 1
    sudo python3 test_oled.py --addr 0x3C
"""
import sys
import time
import argparse

# ─── Console colours ────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def done(msg):
    print(f"  {CYAN}  DONE{RESET}  {msg}")

def fail(msg):
    print(f"  {RED}  FAIL{RESET}  {msg}")

def info(msg):
    print(f"  {CYAN}  info{RESET}  {msg}")

def section(title):
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")

def wait_observe(prompt="Press Enter to continue to the next test..."):
    """Pause and let the user visually inspect the OLED."""
    input(f"\n  {YELLOW}>>> {prompt}{RESET}")


# ─── SSD1306 constants ─────────────────────────────────────────────────────
SSD1306_DISPLAYOFF          = 0xAE
SSD1306_DISPLAYON           = 0xAF
SSD1306_DISPLAYALLON        = 0xA5
SSD1306_DISPLAYALLON_RESUME = 0xA4
SSD1306_NORMALDISPLAY       = 0xA6
SSD1306_INVERTDISPLAY       = 0xA7
SSD1306_SETCONTRAST         = 0x81
SSD1306_SETSTARTLINE        = 0x40
SSD1306_SEGREMAP            = 0xA0
SSD1306_COMSCANDEC          = 0xC8
SSD1306_SETDISPLAYCLOCKDIV  = 0xD5
SSD1306_SETMULTIPLEX        = 0xA8
SSD1306_SETDISPLAYOFFSET    = 0xD3
SSD1306_CHARGEPUMP          = 0x8D
SSD1306_MEMORYMODE          = 0x20
SSD1306_SETCOMPINS          = 0xDA
SSD1306_SETPRECHARGE        = 0xD9
SSD1306_SETVCOMDETECT       = 0xDB

WIDTH  = 128
HEIGHT = 32
PAGES  = HEIGHT // 8


# ─── Tester class ───────────────────────────────────────────────────────────
class OLEDTester:
    def __init__(self, bus_num=1, address=0x3C):
        self.bus_num = bus_num
        self.address = address
        self.bus = None
        self.errors = 0

    def record_fail(self, msg):
        fail(msg)
        self.errors += 1

    # ── 1. I2C bus ──────────────────────────────────────────────────────
    def test_i2c_bus(self):
        section("Test 1: I2C Bus")
        try:
            from smbus2 import SMBus
        except ImportError:
            self.record_fail("smbus2 not installed.  Run: pip install smbus2")
            return False

        info("smbus2 module found")

        try:
            self.bus = SMBus(self.bus_num)
            info(f"/dev/i2c-{self.bus_num} opened successfully")
        except FileNotFoundError:
            self.record_fail(
                f"/dev/i2c-{self.bus_num} does not exist.\n"
                f"         Enable I2C: sudo raspi-config > Interface > I2C\n"
                f"         Or check /boot/firmware/config.txt has dtparam=i2c_arm=on"
            )
            return False
        except PermissionError:
            self.record_fail(
                f"Permission denied on /dev/i2c-{self.bus_num}.\n"
                f"         Run with sudo, or: sudo usermod -aG i2c $USER"
            )
            return False

        return True

    # ── 2. Device scan ──────────────────────────────────────────────────
    def test_device_scan(self):
        section("Test 2: I2C Device Scan")
        found = []
        for addr in range(0x03, 0x78):
            try:
                self.bus.read_byte(addr)
                found.append(addr)
            except Exception:
                pass

        if found:
            info(f"Found {len(found)} I2C device(s):")
            for addr in found:
                label = ""
                if addr in (0x3C, 0x3D):
                    label = " <-- SSD1306 OLED"
                elif addr == 0x68:
                    label = " <-- DS1307 RTC"
                print(f"         0x{addr:02X}{label}")
        else:
            self.record_fail("No I2C devices found!  Check wiring / solder joints.")
            return False

        if self.address in found:
            info(f"Target OLED address 0x{self.address:02X} detected")
            return True
        else:
            self.record_fail(
                f"Target address 0x{self.address:02X} NOT found!\n"
                f"         OLED may be disconnected, mis-addressed, or dead.\n"
                f"         Try: sudo i2cdetect -y {self.bus_num}"
            )
            return False

    # ── 3. Basic command write ──────────────────────────────────────────
    def test_basic_command(self):
        section("Test 3: I2C Command Write")

        cmds = [
            (SSD1306_DISPLAYOFF,         "Display OFF"),
            (SSD1306_SETDISPLAYCLOCKDIV, "Set clock divider"),
            (0x80,                       "  clock value"),
            (SSD1306_SETMULTIPLEX,       "Set MUX ratio"),
            (0x1F,                       "  MUX=31 (32 rows)"),
        ]

        all_ok = True
        for cmd, desc in cmds:
            try:
                self.bus.write_byte_data(self.address, 0x00, cmd)
            except OSError as e:
                self.record_fail(f"Command 0x{cmd:02X} ({desc}) failed: {e}")
                all_ok = False

        if all_ok:
            info("All 5 basic commands sent without I2C error")
        return all_ok

    # ── 4. Full init sequence ───────────────────────────────────────────
    def test_full_init(self):
        section("Test 4: Full SSD1306 Init (128x32)")

        init_sequence = [
            SSD1306_DISPLAYOFF,
            SSD1306_SETDISPLAYCLOCKDIV, 0xB1,
            SSD1306_SETMULTIPLEX, 0x1F,
            SSD1306_SETDISPLAYOFFSET, 0x10,
            SSD1306_SETSTARTLINE | 0x0,
            SSD1306_SEGREMAP | 0x1,
            SSD1306_COMSCANDEC,
            0x82, 0x00,
            SSD1306_SETCONTRAST, 0x4D,
            SSD1306_SETPRECHARGE, 0x62,
            SSD1306_SETVCOMDETECT, 0x3F,
            SSD1306_DISPLAYALLON_RESUME,
            SSD1306_NORMALDISPLAY,
            0xAD, 0x8B,
            0xAF,
        ]

        try:
            for cmd in init_sequence:
                self.bus.write_byte_data(self.address, 0x00, cmd)
                time.sleep(0.001)
            info(f"Init sequence sent ({len(init_sequence)} commands, no I2C error)")
            return True
        except OSError as e:
            self.record_fail(f"Init sequence failed mid-way: {e}")
            return False

    # ── 5. All-pixels-on (hardware level) ───────────────────────────────
    def test_all_pixels_on(self):
        section("Test 5: Hardware All-Pixels-On  *** KEY TEST ***")
        info("Sends SSD1306 command 0xA5 -- lights every pixel")
        info("Does NOT depend on GDDRAM; driven directly by the chip")
        info("==> LOOK AT THE SCREEN: should be completely WHITE <==")

        try:
            self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYON)
            time.sleep(0.01)
            self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYALLON)
            done("All-pixels-on command sent")
            wait_observe("Is the screen fully white?  Press Enter...")
            self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYALLON_RESUME)
            return True
        except OSError as e:
            self.record_fail(f"All-pixels-on failed: {e}")
            return False

    # ── 6. All-pixels-off (clear) ───────────────────────────────────────
    def test_all_pixels_off(self):
        section("Test 6: Clear Screen (all black)")
        info("Writing 0x00 to all GDDRAM -- screen should be BLACK")
        info("==> LOOK AT THE SCREEN: should be completely BLACK <==")

        try:
            from smbus2 import i2c_msg
            for page in range(PAGES):
                self.bus.write_byte_data(self.address, 0x00, 0xB0 + page)
                self.bus.write_byte_data(self.address, 0x00, 0x00)
                self.bus.write_byte_data(self.address, 0x00, 0x10)
                data = [0x40] + [0x00] * WIDTH
                msg = i2c_msg.write(self.address, data)
                self.bus.i2c_rdwr(msg)

            done("Clear-screen data sent")
            wait_observe("Is the screen fully black?  Press Enter...")
            return True
        except OSError as e:
            self.record_fail(f"Clear screen failed: {e}")
            return False

    # ── 7. Checkerboard ─────────────────────────────────────────────────
    def test_checkerboard(self):
        section("Test 7: Checkerboard Pattern")
        info("Alternating 0xAA / 0x55 -- should show an even grid")
        info("==> LOOK AT THE SCREEN: should show a fine checkerboard <==")

        try:
            from smbus2 import i2c_msg
            for page in range(PAGES):
                self.bus.write_byte_data(self.address, 0x00, 0xB0 + page)
                self.bus.write_byte_data(self.address, 0x00, 0x00)
                self.bus.write_byte_data(self.address, 0x00, 0x10)
                pattern = [0xAA if (col + page) % 2 == 0 else 0x55
                           for col in range(WIDTH)]
                data = [0x40] + pattern
                msg = i2c_msg.write(self.address, data)
                self.bus.i2c_rdwr(msg)

            done("Checkerboard data sent")
            wait_observe("Do you see an even checkerboard?  Press Enter...")
            return True
        except OSError as e:
            self.record_fail(f"Checkerboard test failed: {e}")
            return False

    # ── 8. Contrast sweep ───────────────────────────────────────────────
    def test_contrast_sweep(self):
        section("Test 8: Contrast Sweep")
        info("Sweeping contrast 0 -> 255 -> 0")
        info("==> LOOK AT THE SCREEN: brightness should ramp up then down <==")

        try:
            self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYALLON)
            time.sleep(0.3)

            for contrast in range(0, 256, 8):
                self.bus.write_byte_data(self.address, 0x00, SSD1306_SETCONTRAST)
                self.bus.write_byte_data(self.address, 0x00, contrast)
                time.sleep(0.08)

            for contrast in range(255, -1, -8):
                self.bus.write_byte_data(self.address, 0x00, SSD1306_SETCONTRAST)
                self.bus.write_byte_data(self.address, 0x00, max(0, contrast))
                time.sleep(0.08)

            # Restore defaults
            self.bus.write_byte_data(self.address, 0x00, SSD1306_SETCONTRAST)
            self.bus.write_byte_data(self.address, 0x00, 0x4D)
            self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYALLON_RESUME)

            done("Contrast sweep complete")
            wait_observe("Did brightness change visibly?  Press Enter...")
            return True
        except OSError as e:
            self.record_fail(f"Contrast sweep failed: {e}")
            return False

    # ── 9. Invert display ───────────────────────────────────────────────
    def test_invert(self):
        section("Test 9: Display Invert")
        info("Toggling normal / inverted 4 times")
        info("==> LOOK AT THE SCREEN: black and white should swap <==")

        try:
            for _ in range(4):
                self.bus.write_byte_data(self.address, 0x00, SSD1306_INVERTDISPLAY)
                time.sleep(0.5)
                self.bus.write_byte_data(self.address, 0x00, SSD1306_NORMALDISPLAY)
                time.sleep(0.5)

            done("Invert toggle complete")
            wait_observe("Did colours alternate?  Press Enter...")
            return True
        except OSError as e:
            self.record_fail(f"Invert test failed: {e}")
            return False

    # ── 10. Text rendering via Pillow ───────────────────────────────────
    def test_text_render(self):
        section("Test 10: Pillow Text Rendering")
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            self.record_fail("Pillow not installed.  Run: pip install Pillow")
            return False

        info("Pillow module found")

        try:
            from smbus2 import i2c_msg

            image = Image.new('1', (WIDTH, HEIGHT))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.load_default_imagefont()
                info("Using Pillow built-in bitmap font (load_default_imagefont)")
            except AttributeError:
                font = ImageFont.load_default()
                info("Using Pillow default font (load_default)")

            draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline=255, fill=0)
            draw.text((4, 2),  "OLED TEST OK!", font=font, fill=255)
            draw.text((4, 14), "128x32 SSD1306", font=font, fill=255)
            draw.text((4, 23), f"addr=0x{self.address:02X} bus={self.bus_num}", font=font, fill=255)

            # Convert to SSD1306 buffer format
            pix = image.load()
            buf = []
            for page in range(PAGES):
                for x in range(WIDTH):
                    bits = 0
                    for bit in [0, 1, 2, 3, 4, 5, 6, 7]:
                        bits = bits << 1
                        bits |= 0 if pix[(x, page * 8 + 7 - bit)] == 0 else 1
                    buf.append(bits)

            pg = 0
            for i in range(0, len(buf), WIDTH):
                self.bus.write_byte_data(self.address, 0x00, 0xB0 + pg)
                self.bus.write_byte_data(self.address, 0x00, 0x00)
                self.bus.write_byte_data(self.address, 0x00, 0x10)
                data = [0x40] + buf[i:i + WIDTH]
                msg = i2c_msg.write(self.address, data)
                self.bus.i2c_rdwr(msg)
                pg += 1

            done("Text rendered and written to display")
            info("Expected on screen:")
            info('    +----------------------+')
            info('    | OLED TEST OK!        |')
            info('    | 128x32 SSD1306       |')
            info(f'    | addr=0x{self.address:02X} bus={self.bus_num}      |')
            info('    +----------------------+')
            wait_observe("Can you read the text clearly?  Press Enter...")
            return True
        except OSError as e:
            self.record_fail(f"Text render write failed: {e}")
            return False

    # ── 11. Display on / off ────────────────────────────────────────────
    def test_on_off(self):
        section("Test 11: Display ON / OFF Toggle")
        info("Toggling display power 3 times")
        info("==> LOOK AT THE SCREEN: should blink on and off <==")

        try:
            for _ in range(3):
                self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYOFF)
                time.sleep(0.8)
                self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYON)
                time.sleep(0.8)
            done("ON/OFF toggle complete")
            wait_observe("Did the screen blink on and off?  Press Enter...")
            return True
        except OSError as e:
            self.record_fail(f"ON/OFF test failed: {e}")
            return False

    # ── Summary report ──────────────────────────────────────────────────
    def report(self):
        section("Diagnostic Summary")

        if self.errors == 0:
            print(f"  {GREEN}{BOLD}All commands sent successfully (no I2C errors).{RESET}")
            print()
            print(f"  If you saw correct output for every visual test above,")
            print(f"  the OLED hardware is working fine.")
        else:
            print(f"  {RED}{BOLD}{self.errors} I2C error(s) detected.{RESET}")
            print()
            print(f"  {BOLD}Troubleshooting:{RESET}")
            print(f"  1. Check I2C wiring:  sudo i2cdetect -y {self.bus_num}")
            print(f"  2. Check ribbon cable / solder joints")
            print(f"  3. If address is detected but display never responds,")
            print(f"     the OLED is likely burned out")
            print(f"  4. Try lowering I2C speed:")
            print(f"     Add to /boot/firmware/config.txt:")
            print(f"       dtparam=i2c_arm_baudrate=50000")
            print(f"  5. If Test 5 (all-pixels-on) showed nothing")
            print(f"     -> OLED panel is almost certainly {RED}damaged{RESET}")
        print()

    # ── Run all ─────────────────────────────────────────────────────────
    def run_all(self):
        print(f"\n{BOLD}{'=' * 60}{RESET}")
        print(f"{BOLD}  TFOLED -- OLED Diagnostic Tool{RESET}")
        print(f"{BOLD}  Target : I2C bus {self.bus_num}, address 0x{self.address:02X}{RESET}")
        print(f"{BOLD}  Display: SSD1306 {WIDTH}x{HEIGHT}{RESET}")
        print(f"{BOLD}{'=' * 60}{RESET}")

        # Connection tests (fatal if they fail)
        if not self.test_i2c_bus():
            self.report()
            return
        if not self.test_device_scan():
            self.report()
            return
        if not self.test_basic_command():
            self.report()
            return
        self.test_full_init()

        # Visual tests — user must observe
        print(f"\n  {YELLOW}The following tests require you to watch the OLED screen.{RESET}")
        print(f"  {YELLOW}After each test you will be asked to confirm what you see.{RESET}")
        input(f"\n  Press Enter to begin visual tests...")

        self.test_all_pixels_on()
        self.test_all_pixels_off()
        self.test_checkerboard()
        self.test_contrast_sweep()
        self.test_invert()
        self.test_text_render()
        self.test_on_off()

        self.report()

        # Clear display before exit
        if self.bus:
            info("Clearing display...")
            try:
                from smbus2 import i2c_msg
                for page in range(PAGES):
                    self.bus.write_byte_data(self.address, 0x00, 0xB0 + page)
                    self.bus.write_byte_data(self.address, 0x00, 0x00)
                    self.bus.write_byte_data(self.address, 0x00, 0x10)
                    data = [0x40] + [0x00] * WIDTH
                    msg = i2c_msg.write(self.address, data)
                    self.bus.i2c_rdwr(msg)
                self.bus.write_byte_data(self.address, 0x00, SSD1306_DISPLAYOFF)
                done("Display cleared and turned off")
            except Exception:
                pass
            self.bus.close()


def main():
    parser = argparse.ArgumentParser(
        description="TFOLED -- SSD1306 OLED Diagnostic Tool"
    )
    parser.add_argument(
        "--bus", type=int, default=1,
        help="I2C bus number (default: 1)"
    )
    parser.add_argument(
        "--addr", type=lambda x: int(x, 0), default=0x3C,
        help="OLED I2C address (default: 0x3C)"
    )
    args = parser.parse_args()

    tester = OLEDTester(bus_num=args.bus, address=args.addr)
    try:
        tester.run_all()
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}Interrupted by user{RESET}")
        if tester.bus:
            tester.bus.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
