from flask import Flask, jsonify, render_template, request, Response
from motor_controller import MotorController
from TelescopeController import TelescopeController
from Angle import Angle 
import threading
from time import sleep
from camera_stream import CameraStream


app = Flask(__name__)

camera_stream = CameraStream(
    camera_index=0,
    width=1280,
    height=720,
    fps=30,
    jpeg_quality=80,
)

altitude = 90 # telescope pointed straight up
azimuth = 0  # Pointed to some reference for now probably east for now

NEMA17_Motor = MotorController(17, 27, 0.01, 1.8, 1/2)
NEMA23_Motor = MotorController(23, 24, 0.01, 1.8, 1/2)

"""Since the NEMA17 is responsible for the altitude and it is attached to a 
    sprocket gear setup I have to take that into Account when doing the 
    calculations for the angle per step, θa = θb​ * (Tb/Ta)"""
   
T_b = 12 # Small Sprocket teeth, this is the sprocket attached to the motor 
T_a = 120 # large sprocket teeth, this is the sprocket attached to the telescope
theta_b = NEMA17_Motor.get_angle_per_step() 
theta_a = theta_b * (T_b/T_a) # True degrees of rotation per step for the altitude  

"""Similarly the NEMA23 is used to control the Azimuth but it used 2 basic spur gears
    so the formula should be the exact same."""
    
T_driver = 30 # Driver Teeth 
T_driven = 200 # Driven Teeth 

theta_driver = NEMA23_Motor.get_angle_per_step()
theta_driven = theta_driver * (T_driver/T_driven) # True degrees of rotation per step for the azimuth   
    
print(theta_a)
print(theta_driven)

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
    global altitude, azimuth
    while True:
        with lock:
            should_keep_moving = movement_flags.get(action, False)
        if not should_keep_moving:
            break
        if action == "left":
            print("moving left")
            # not implemented yet
            NEMA23_Motor.step_clockwise()
            azimuth += theta_driven
        elif action == "right":
            # not implemented yet
            print("moving right")
            NEMA23_Motor.step_counterclockwise()
            azimuth -= theta_driven
        elif action == "up":
            print("moving up")
            NEMA17_Motor.step_counterclockwise()
            altitude += theta_a
        elif action == "down":
            print("moving down")
            NEMA17_Motor.step_clockwise()
            altitude -= theta_a        

    with lock:
        movement_threads.pop(action, None)


@app.route("/")
def index():
    return render_template("index.html")

    
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "altitude": round(altitude, 3),
        "azimuth" : round(azimuth, 3)
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
            
    return jsonify({"altitude": round(altitude, 3)})

    
@app.route("/movement_unpressed", methods=["POST"])
def movement_unpressed():
    data = request.get_json()
    action = data.get("action")
    print(f"button was unpressed: {action}")
    with lock:
        movement_flags[action] = False
    return jsonify({"altitude": round(altitude, 3)})


@app.route("/move_to", methods=["POST"])
def move_to():
    data = request.get_json()
    altitude = float(data.get("altitude"))
    azimuth = float(data.get("azimuth"))
    print(f"Move to: al: {altitude}|azi: {azimuth}")
    angle = Angle(altitude, azimuth)
    # TelescopeController.move_to(angle)    
    return jsonify({"status": "ok"})

@app.route("/stop_move_to", methods=["POST"])
def stop_move_to():
    TelescopeController.stop()
    print("stop button was pressed")
    return jsonify({"status": "ok"})

@app.route("/video_feed")
def video_feed():
    camera_stream.start()
    return Response(
        camera_stream.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@app.route("/test", methods=["POST"])
def test():
    angle = Angle(52, 1)
    TelescopeController.move_to(angle)
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)