from flask import Flask, jsonify, render_template, request, Response
from MotorController import StepperMotor
from TelescopeController import TelescopeController
from CelestialObject import CelestialObject
from Angle import Angle 
import threading
from time import sleep 
from CameraStream import CameraStream


app = Flask(__name__)

# camera_stream = CameraStream(
#     camera_index=0,
#     width=1280,
#     height=720,
#     fps=30,
#     jpeg_quality=80,
# )

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

def move_continuously(action):
    while True:
        with lock:
            should_keep_moving = movement_flags.get(action, False)
        if not should_keep_moving:
            break
        if action == "left":
            print("moving left")
            NEMA23_Motor.step_clockwise()
            TelescopeController.current_az += TelescopeController.get_az_angle()
        elif action == "right":
            print("moving right")
            NEMA23_Motor.step_counterclockwise()
            TelescopeController.current_az -= TelescopeController.get_az_angle()
        elif action == "up":
            print("moving up")
            NEMA17_Motor.step_counterclockwise()
            TelescopeController.current_alt += TelescopeController.get_alt_angle()
        elif action == "down":
            print("moving down")
            NEMA17_Motor.step_clockwise()
            TelescopeController.current_alt -= TelescopeController.get_alt_angle()    

    with lock:
        movement_threads.pop(action, None)


@app.route("/")
def index():
    return render_template("index.html")

    
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "altitude": round(TelescopeController.current_alt, 3),
        "azimuth" : round(TelescopeController.current_az, 3),
        "moving": TelescopeController.moving,
    })


@app.route("/movement_pressed", methods=["POST"])
def movement_pressed():
    data = request.get_json()
    action = data.get("action")
    print(f"button was pressed down: {action}")
    with lock:
        movement_flags[action] = True
        if action not in movement_threads:
            thread = threading.Thread(target=move_continuously, args=(action,), daemon=True)
            movement_threads[action] = thread
            thread.start()
            
    return jsonify({"status": "ok"})

    
@app.route("/movement_unpressed", methods=["POST"])
def movement_unpressed():
    data = request.get_json()
    action = data.get("action")
    print(f"button was unpressed: {action}")
    with lock:
        movement_flags[action] = False
    return jsonify({"status": "ok"})


@app.route("/move_to", methods=["POST"])
def move_to():
    global moving 
    
    if moving:
        return jsonify({
            "status": "busy",
            "message": "Telescope is already moving."
        }), 409
        
    moving = True 
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
            "message": str(e)
        }), 500
    finally: 
        moving = False


@app.route("/stop_move_to", methods=["POST"])
def stop_move_to():
    TelescopeController.stop()
    print("stop button was pressed")
    moving = False
    return jsonify({"status": "ok"})


# @app.route("/video_feed")
# def video_feed():
#     camera_stream.start()
#     return Response(
#         camera_stream.generate_frames(),
#         mimetype="multipart/x-mixed-replace; boundary=frame",
#     )


# @app.route("/update_camera", methods=["POST"])
# def update_camera():
#     data = request.get_json()
#     camera_stream.set_controls(
#         exposure=data.get("exposure"), 
#         gain=data.get("gain"), 
#         brightness=data.get("brightness"))
    
#     return jsonify({"status": "ok"})

@app.route("/test", methods=["POST"])
def test():
    print("test was called")
    # cel_object = CelestialObject("jupiter")
    # TelescopeController.start_tracking(cel_object)

    angle = Angle(95,95)
    TelescopeController.move_to(angle)
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