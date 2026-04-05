from flask import Flask, jsonify, render_template, request
from motor_controller import MotorController
import threading
from time import sleep
 

app = Flask(__name__)

altitude = 90
motor = MotorController(17,27,0.01, 1.8, 1/2)

"""Since Motor is attached to a sprocket gear setup I have to take that into
   Account when doing the calculations for the angle per step, θa = θb​ * (Tb/Ta)"""
   
T_b = 12 # Small Sprocket teeth, this is the sprocket attached to the motor 
T_a = 120 # large sprocket teeth, this is the sprocket attached to the telescope
theta_b = motor.get_angle_per_step() 
theta_a = theta_b * (T_b/T_a) # This should be the true degrees of rotation per step for the telescope
   
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
    global altitude
    while True:
        with lock:
            should_keep_moving = movement_flags.get(action, False)
        if not should_keep_moving:
            break
        if action == "left":
            # not implemented yet
            pass
        elif action == "right":
            # not implemented yet
            pass
        elif action == "up":
            print("moving up")
            # motor.step_counterclockwise()
            altitude += theta_a
        elif action == "down":
            print("moving down")
            # motor.step_clockwise()
            altitude -= theta_a        
        sleep(0.02)

    with lock:
        movement_threads.pop(action, None)


@app.route("/")
def index():
    return render_template("index.html")

    
@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "altitude": round(altitude, 3)
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


@app.route("/command", methods=["POST"])
def command():
    global altitude

    data = request.get_json()
    action = data.get("action")

    if action == "move_up":
        altitude += 1
        # motor.step_clockwise()
    elif action == "move_down":
        altitude -= 1
        # motor.step_counterclockwise()
    return jsonify({
        "altitude": altitude
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)