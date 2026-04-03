from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

altitude = 0


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "altitude": altitude
    })


@app.route("/command", methods=["POST"])
def command():
    global altitude

    data = request.get_json()
    action = data.get("action")

    if action == "move_up":
        altitude += 1
    elif action == "move_down":
        altitude -= 1

    return jsonify({
        "altitude": altitude
    })


if __name__ == "__main__":
    app.run(debug=True)