import logging
from functools import wraps

from flask import Flask, jsonify, render_template, request, Response, abort
from werkzeug.exceptions import HTTPException

import config
from MotorController import StepperMotor
from TelescopeController import TelescopeController, TelescopeError, TelescopeBusyError
from CelestialObject import CelestialObject
from CameraStream import CameraStream
from TimeKeeper import time_keeper

# Configure logging before any hardware objects are created, so their start-up
# messages (handshake, GPS, UART) aren't lost.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s <%(name)s>:: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")

app = Flask(__name__)

camera_stream = CameraStream()

NEMA17_Motor = StepperMotor(config.MOTOR_STEP_ANGLE, config.MICROSTEPPING, "elevation")
NEMA23_Motor = StepperMotor(config.MOTOR_STEP_ANGLE, config.MICROSTEPPING, "azimuth")

if config.SIMULATE_HARDWARE:
    from SimulatedSerial import SimulatedSerial
    mcu_link = SimulatedSerial()
else:
    mcu_link = None     # TelescopeController opens the real UART

telescope = TelescopeController(
    NEMA17_Motor, NEMA23_Motor,
    config.EL_DRIVER_TEETH, config.EL_DRIVEN_TEETH,
    config.AZ_DRIVER_TEETH, config.AZ_DRIVEN_TEETH,
    ser=mcu_link,
    start_gps=config.GPS_ENABLED and not config.SIMULATE_HARDWARE,
)


# ---------- Error handling ----------
# TelescopeController raises; these turn the exceptions into JSON replies
# the front end shows in its event log.

@app.errorhandler(TelescopeBusyError)
def handle_busy(e):
    return jsonify({"status": "busy", "message": str(e)}), 409


@app.errorhandler(TelescopeError)
def handle_refused(e):
    return jsonify({"status": "error", "message": str(e)}), 400


@app.errorhandler(Exception)
def handle_unexpected(e):
    if isinstance(e, HTTPException):
        return jsonify({"status": "error", "message": e.description}), e.code
    logger.exception("Unhandled error on %s", request.path)
    return jsonify({"status": "error", "message": str(e)}), 500


def require_idle(allow_calibrating=False):
    # API-level busy check (the controller checks again before sending)
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if telescope.moving:
                raise TelescopeBusyError("Telescope is already moving.")
            if telescope.calibrating and not allow_calibrating:
                raise TelescopeBusyError("Telescope is calibrating.")
            return view(*args, **kwargs)
        return wrapper
    return decorator


def get_json_field(name):
    data = request.get_json(silent=True) or {}
    if data.get(name) is None:
        abort(400, description=f"Missing '{name}'.")
    return data[name]


def get_number(name):
    try:
        return float(get_json_field(name))
    except (TypeError, ValueError):
        abort(400, description=f"'{name}' must be a number.")


def get_celestial_object(name):
    try:
        return CelestialObject(str(name))
    except ValueError as e:
        abort(400, description=str(e))


# ---------- Routes ----------

@app.route("/")
def index():
    return render_template(
        "index.html",
        el_min=config.EL_MIN,
        el_max=config.EL_MAX,
        min_visible_elevation=config.MIN_VISIBLE_ELEVATION,
    )


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "altitude": round(telescope.current_el, 3),
        "azimuth": round(telescope.current_az, 3),
        "azimuth_error": round(telescope.error_az, 3),
        "elevation_error": round(telescope.error_el, 3),
        "az_wrap": None if telescope.az_wrap is None else round(telescope.az_wrap, 1),
        "moving": telescope.moving,
        "sys_ready": telescope.sys_ready,
        "gps_ready": telescope.gps.has_fix,
        "longitude": telescope.gps.lon,
        "latitude": telescope.gps.lat,
        "pulse_delay": telescope.pulse_delay,
        "calibrating": telescope.calibrating,
        "tracking": telescope.tracking,
        "camera_ok": camera_stream.is_streaming(),
        "time_source": time_keeper.source,
    })


@app.route("/sync_time", methods=["POST"])
def sync_time():
    # The dashboard sends the laptop's clock; used when there's no GPS time yet
    epoch_ms = get_number("epoch_ms")
    time_keeper.update_from_laptop(epoch_ms)
    return jsonify({"status": "ok", "time_source": time_keeper.source})


@app.route("/movement_pressed", methods=["POST"])
@require_idle(allow_calibrating=True)   # jogging is how you centre Polaris
def movement_pressed():
    action = get_json_field("action")
    logger.info("Move %s button was pressed down", action)
    telescope.jog(action)
    return jsonify({"status": "ok"})


@app.route("/movement_heartbeat", methods=["POST"])
def movement_heartbeat():
    # Sent every ~200 ms while a jog button is held; silence stops the mount
    telescope.jog_heartbeat()
    return jsonify({"status": "ok"})


@app.route("/movement_unpressed", methods=["POST"])
def movement_unpressed():
    data = request.get_json(silent=True) or {}
    logger.info("Move %s button was unpressed", data.get("action"))
    telescope.stop()
    return jsonify({"status": "ok"})


@app.route("/set_pulse", methods=["POST"])
@require_idle(allow_calibrating=True)
def set_pulse():
    delay = get_number("delay")
    if not delay.is_integer():
        abort(400, description="Pulse delay must be a whole number of ms.")
    telescope.set_pulse(int(delay))
    return jsonify({"status": "ok"})


@app.route("/move_to", methods=["POST"])
@require_idle()
def move_to():
    elevation = get_number("altitude")
    azimuth = get_number("azimuth")
    logger.info("Move to: altitude: %s | azimuth: %s", elevation, azimuth)
    telescope.stop_tracking()
    telescope.move_to((elevation, azimuth))
    return jsonify({"status": "ok"})


@app.route("/stop_move_to", methods=["POST"])
def stop_move_to():
    logger.info("Stop button was pressed")
    telescope.stop()
    return jsonify({"status": "ok"})


@app.route("/video_feed")
def video_feed():
    try:
        camera_stream.start()
    except RuntimeError as e:
        # No camera plugged in: a clean 503 instead of a traceback per page load
        logger.warning("%s", e)
        return Response(str(e), status=503, mimetype="text/plain")
    return Response(
        camera_stream.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/update_camera", methods=["POST"])
def update_camera():
    data = request.get_json(silent=True) or {}
    camera_stream.set_controls(
        exposure=data.get("exposure"),
        gain=data.get("gain"),
        brightness=data.get("brightness"))
    return jsonify({"status": "ok"})


@app.route("/planets")
def get_planets():
    planets = [
        {"name": "Moon", "image": "moon.png"},
        {"name": "Mercury", "image": "mercury.png"},
        {"name": "Venus", "image": "venus.png"},
        {"name": "Mars", "image": "mars.png"},
        {"name": "Jupiter", "image": "jupiter.png"},
        {"name": "Saturn", "image": "saturn.png"},
        {"name": "Uranus", "image": "uranus.png"},
        {"name": "Neptune", "image": "neptune.png"}
    ]

    coords = telescope.gps.get_coords()
    for planet in planets:
        cel_obj = CelestialObject(planet["name"])
        position = cel_obj.get_astrometric_coords(coords)
        planet["altitude"] = round(position.altitude, 2)
        planet["azimuth"] = round(position.azimuth, 2)
        planet["visible"] = position.altitude >= config.MIN_VISIBLE_ELEVATION
    return jsonify(planets)


@app.route("/select_planet", methods=["POST"])
@require_idle()
def select_planet():
    planet = get_json_field("name")
    logger.info("Move to: %s", planet)
    cel_object = get_celestial_object(planet)
    telescope.stop_tracking()
    telescope.move_to_object(cel_object)    # refuses targets below the minimum elevation
    return jsonify({"status": "ok"})


@app.route("/track_planet", methods=["POST"])
@require_idle()
def track_planet():
    planet = get_json_field("name")
    logger.info("Live track: %s", planet)
    cel_object = get_celestial_object(planet)
    telescope.track_object(cel_object)
    return jsonify({"status": "ok"})


@app.route("/startCalibration", methods=["POST"])
@require_idle()
def startCalibration():
    telescope.calibrate()
    return jsonify({"status": "ok"})


@app.route("/resetOrigin", methods=["POST"])
@require_idle()
def resetOrigin():
    telescope.reset_origin()
    return jsonify({"status": "ok"})


@app.route("/finishCalibration", methods=["POST"])
@require_idle(allow_calibrating=True)
def finishCalibration():
    telescope.finish_calibration()
    return jsonify({"status": "ok"})


@app.route("/test", methods=["POST"])
def test():
    logger.info("Test was called. Calibrating: %s, moving: %s, tracking: %s",
                telescope.calibrating, telescope.moving, telescope.tracking)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    if not config.LOCATION_CONFIGURED:
        logger.warning("DEFAULT_LATITUDE/DEFAULT_LONGITUDE aren't set in .env; "
                       "planet positions are wrong until the GPS has a fix.")
    if config.SIMULATE_HARDWARE:
        logger.warning("SIMULATE_HARDWARE is on: using SimulatedSerial, not the real MCU.")

    # this just ignores the spam from the /status and jog heartbeat requests
    class IgnoreStatusFilter(logging.Filter):
        def filter(self, record):
            message = record.getMessage()
            return "GET /status" not in message and "POST /movement_heartbeat" not in message

    werkzeug_log = logging.getLogger("werkzeug")
    werkzeug_log.addFilter(IgnoreStatusFilter())
    app.run(host=config.HOST, port=config.PORT, debug=False)
