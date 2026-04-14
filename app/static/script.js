let currentAction = null;

async function mouseDown(action) {
    currentAction = action
    const response = await fetch("/movement_pressed", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ action: action })
    });
    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;

}

async function mouseUp(action) {
    const response = await fetch("/movement_unpressed", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ action: action })
    });
    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;
}

document.addEventListener("mouseup", async function () {
    if (currentAction !== null) {
        await fetch("/movement_unpressed", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ action: currentAction })
        });

        currentAction = null;
    }
});

document.getElementById("move_to").addEventListener("submit", async function (e) {
    e.preventDefault();

    const altitude = document.getElementById("move_altitude").value;
    const azimuth = document.getElementById("move_azimuth").value;
    try {
        const response = await fetch("/move_to", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                azimuth: azimuth,
                altitude: altitude
            })
        });

        const data = await response.json();
        console.log(data);

        if (response.status === 409) {
            alert(data.message || "Telescope is already moving.");
        } else if (!response.ok) {
            alert(data.message || "Something went wrong.");
        } else {
            console.log("Move finished successfully.");
        }
    } catch (error) {
        console.error("Request failed:", error);
        alert("Could not reach the server.");
    }
});

async function test() {
    await fetch("/test", {
        method: "POST"
    });
}

async function stop_move_to() {
    await fetch("/stop_move_to", {
        method: "POST"
    });
    
}

document.addEventListener("DOMContentLoaded", () => {
    const brightnessRange = document.getElementById("brightnessRange");
    const brightnessValue = document.getElementById("brightnessValue");

    const exposureRange = document.getElementById("exposureRange");
    const exposureValue = document.getElementById("exposureValue");

    const gainRange = document.getElementById("gainRange");
    const gainValue = document.getElementById("gainValue");

    let timeout = null;

    function sendToBackend() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            fetch("/update_camera", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    brightness: brightnessRange.value,
                    exposure: exposureRange.value,
                    gain: gainRange.value
                })
            });
        }, 50);
    }

    brightnessValue.innerHTML = brightnessRange.value;
    exposureValue.innerHTML = exposureRange.value;
    gainValue.innerHTML = gainRange.value;

    brightnessRange.oninput = function () {
        brightnessValue.innerHTML = this.value;
        sendToBackend();
    };

    exposureRange.oninput = function () {
        exposureValue.innerHTML = this.value;
        sendToBackend();
    };

    gainRange.oninput = function () {
        gainValue.innerHTML = this.value;
        sendToBackend();
    };
});

async function fetchStatus() {
    const response = await fetch("/status");
    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;
    document.getElementById("azimuth").textContent = data.azimuth;

    const moving = data.moving ? "Yes" : "No";
    document.getElementById("moving").textContent = moving;
}


setInterval(fetchStatus, 100);