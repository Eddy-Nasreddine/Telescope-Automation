let currentAction = null;

async function sendCommand(action) {
    const response = await fetch("/command", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ action: action })
    });

    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;
}

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

document.getElementById("move_to").addEventListener("submit", async function(e) {
    e.preventDefault(); 

    const altitude = document.getElementById("move_altitude").value;
    const azimuth = document.getElementById("move_azimuth").value;

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

async function fetchStatus() {
    const response = await fetch("/status");
    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;
    document.getElementById("azimuth").textContent = data.azimuth;

}


// setInterval(fetchStatus, 100);