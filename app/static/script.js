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



async function fetchStatus() {
    const response = await fetch("/status");
    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;
}


setInterval(fetchStatus, 100);