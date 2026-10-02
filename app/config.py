"""
Project-wide settings in one place.

Values marked "must match main.c" are also hard-coded in the STM32 firmware;
change both together. Private values (your location) come from the .env file
in the repo root, which git ignores. See .env.example.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# ---------- Run mode ----------
# True runs everything against SimulatedSerial (no Pi hardware needed).
SIMULATE_HARDWARE = _env_bool("SIMULATE_HARDWARE", False)

# ---------- Web server ----------
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT") or 5000)

# ---------- Serial links ----------
MCU_PORT = "/dev/ttyAMA0"
MCU_BAUD = 115200
GPS_PORT = "/dev/ttyAMA3"
GPS_BAUD = 9600
GPS_ENABLED = True

# ---------- Motors and gearing ----------
MOTOR_STEP_ANGLE = 1.8      # degrees per full step (NEMA 17 and NEMA 23)
MICROSTEPPING = 1 / 2
EL_DRIVER_TEETH = 12        # must match main.c (el_angle_per_step = 0.09)
EL_DRIVEN_TEETH = 120
AZ_DRIVER_TEETH = 30        # must match main.c (az_angle_per_step = 0.135)
AZ_DRIVEN_TEETH = 200
MAX_STEPS_PER_COMMAND = 4000    # the firmware parses at most 4 digits per axis

# ---------- Motion limits ----------
EL_MIN = 0.0
EL_MAX = 90.0
HOME_AZ = 90.0              # must match main.c (position after boot / origin reset)
HOME_EL = 90.0              # must match main.c
# Max azimuth travel either side of HOME_AZ, so the motor power cable can't wind up.
# The cable must be untwisted when the mount is at home. Set to None to disable.
AZ_CABLE_LIMIT = 180.0
MIN_VISIBLE_ELEVATION = 25.0    # planets below this can't be selected or tracked

# ---------- Pulse delay (motor speed) ----------
PULSE_DELAY_MIN = 10        # ms
PULSE_DELAY_MAX = 100       # ms

# ---------- Safety timing (seconds) ----------
JOG_HEARTBEAT_TIMEOUT = 0.6     # stop a jog if the browser goes quiet this long
MOTION_TIMEOUT = 2.0            # clear "moving" if the MCU goes silent mid-move
HEARTBEAT_INTERVAL = 2.0        # idle link check (R command) period
HEARTBEAT_TIMEOUT = 0.5         # how long to wait for the R reply
HEARTBEAT_MISSES = 2            # missed replies before the link counts as lost
STOP_ACK_TIMEOUT = 0.3          # wait for the MCU to confirm a stop...
STOP_RETRIES = 3                # ...and resend up to this many times
TRACK_INTERVAL = 5.0            # how often tracking re-points at the target

# ---------- Camera ----------
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30
CAMERA_JPEG_QUALITY = 80
CAMERA_LOST_TIMEOUT = 2.0       # no frames for this long = camera disconnected

# ---------- Observer location (private, from .env) ----------
# Used until the GPS has a fix.
DEFAULT_LATITUDE = _env_float("DEFAULT_LATITUDE", 0.0)
DEFAULT_LONGITUDE = _env_float("DEFAULT_LONGITUDE", 0.0)
LOCATION_CONFIGURED = os.getenv("DEFAULT_LATITUDE") not in (None, "")
