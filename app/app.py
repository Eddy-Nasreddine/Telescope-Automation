from flask import Flask, jsonify, render_template, request, Response
from MotorController import StepperMotor
from TelescopeController import TelescopeController
from CelestialObject import CelestialObject
from Angle import Angle 
import threading
from time import sleep 
from CameraStream import CameraStream


app = Flask(__name__)

camera_stream = CameraStream(
    camera_index=0,
    width=1280,
    height=720,
    fps=30,
    jpeg_quality=80,
)

NEMA17_Motor = StepperMotor(1.8, 1/2)
NEMA23_Motor = StepperMotor(1.8, 1/2)

TelescopeController = TelescopeController(NEMA17_Motor, NEMA23_Motor, 12, 120, 30, 200)

toggle_state = False

movement_flags = {
    "left": False,
    "right": False,
    "up": False,
    "down": False
}

movement_threads = {}
lock = threading.Lock()


@app.route("/")
def index():
    return render_template("index.html")

    
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "altitude": round(TelescopeController.current_alt, 3),
        "azimuth" : round(TelescopeController.current_az, 3),
        "moving": TelescopeController.moving,
        "sys_ready": TelescopeController.sys_ready,
        "pulse_delay": TelescopeController.pulse_delay,
    })


@app.route("/movement_pressed", methods=["POST"])
def movement_pressed():
    data = request.get_json()
    action = data.get("action")
    print(f"Move {action} button was pressed down")
    TelescopeController.jog(action)
    return jsonify({"status": "ok"})

    
@app.route("/movement_unpressed", methods=["POST"])
def movement_unpressed():
    data = request.get_json()
    action = data.get("action")
    print(f"Move {action} button was unpressed")
    TelescopeController.stop()
    return jsonify({"status": "ok"})


@app.route("/set_pulse", methods=["POST"])
def set_pulse():
    data = request.get_json()
    delay = int(data.get("delay"))
    TelescopeController.set_pulse(delay)
    return jsonify({
        "status": "ok"
    })
    
    
@app.route("/move_to", methods=["POST"])
def move_to():
    if TelescopeController.moving:
        return jsonify({
            "status": "busy",
            "message": "Telescope is already moving.",
        }), 409
    try:
        data = request.get_json()
        altitude = float(data.get("altitude"))
        azimuth = float(data.get("azimuth"))
        print(f"Move to: altitude: {altitude} | azimuth: {azimuth}")
        angle = Angle(altitude, azimuth)
        TelescopeController.move_to(angle)   
        print(f"Finished Moving to altitude: {altitude}|azimuth: {azimuth}")
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/stop_move_to", methods=["POST"])
def stop_move_to():
    TelescopeController.stop()
    print("stop button was pressed")
    moving = False
    return jsonify({"status": "ok"})


@app.route("/video_feed")
def video_feed():
    camera_stream.start()
    return Response(
        camera_stream.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/update_camera", methods=["POST"])
def update_camera():
    data = request.get_json()
    camera_stream.set_controls(
        exposure=data.get("exposure"), 
        gain=data.get("gain"), 
        brightness=data.get("brightness"))
    return jsonify({"status": "ok"})


@app.route("/planets")
def get_planets():
    return jsonify([
        {"name": "Moon", "image": "moon.png"},
        {"name": "Mercury", "image": "mercury.png"},
        {"name": "Venus", "image": "venus.png"},
        {"name": "Mars", "image": "mars.png"},
        {"name": "Jupiter", "image": "jupiter.png"},
        {"name": "Saturn", "image": "saturn.png"},
        {"name": "Uranus", "image": "uranus.png"},
        {"name": "Neptune", "image": "neptune.png"}
    ])
    
    
@app.route("/select_planet", methods=["POST"])
def select_planet():
    data = request.get_json()
    planet = data.get("name")
    print(f"Move to: {planet}")
    cel_object = CelestialObject(planet)
    TelescopeController.move_to_object(cel_object)
    return jsonify({"status": "ok"}) 


@app.route("/track_planet", methods=["POST"])
def track_planet():
    data = request.get_json()
    planet = data.get("name")
    print(f"Live track: {planet}")
    cel_object = CelestialObject(planet)
    TelescopeController.track_object()
    return jsonify({"status": "ok"})


@app.route("/test", methods=["POST"])
def test():
    print("test was called")
    cel_object = CelestialObject("jupiter")
    print(cel_object.get_astrometric_coords())
    # TelescopeController.move_to_object(cel_object)

    # angle = Angle(95,95)
    # TelescopeController.move_to(angle)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    import logging

    # this just ignores the spam from the /status request 
    class IgnoreStatusFilter(logging.Filter):
        def filter(self, record):
            message = record.getMessage()
            return "GET /status" not in message

    werkzeug_log = logging.getLogger("werkzeug")
    werkzeug_log.addFilter(IgnoreStatusFilter())
    app.run(host="0.0.0.0", port=5000, debug=False)