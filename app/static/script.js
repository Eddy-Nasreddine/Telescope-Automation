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

async function fetchStatus() {
    const response = await fetch("/status");
    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;
}

fetchStatus();