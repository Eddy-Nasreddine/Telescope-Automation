let currentAction = null;
let selectedPlanet = null;
let isMoving = false;
let wasMoving = false;

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

async function mouseUp(event, action) {
    event.stopPropagation();
    currentAction = null;
    const response = await fetch("/movement_unpressed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

document.getElementById("set_pulse_form").addEventListener("submit", async function (e) {
    e.preventDefault();

    const delay = document.getElementById("delay").value;
    
    try {
        const response = await fetch("/set_pulse", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                delay: delay
            })
        });

        const data = await response.json();


    } catch (error) {
        console.error("Request failed:", error);
        alert("Could not reach the server.");
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
            setAutoStatus("slewing", `Az: ${azimuth}° Alt: ${altitude}°`);
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


async function loadPlanets() {
    const response = await fetch("/planets");
    const planets = await response.json();

    const container = document.getElementById("planet_list");
    container.innerHTML = "";

    planets.forEach(planet => {
        const card = document.createElement("div");
        card.className = "planet-card";
        card.innerHTML = `
            <img src="/static/images/${planet.image}" alt="${planet.name}">
            <h3>${planet.name}</h3>
        `;
        card.addEventListener("click", (event) => onPlanetClick(event, planet));
        container.appendChild(card);
    });
}

function onPlanetClick(event, planet) {
    document.querySelectorAll(".planet-card").forEach(c => c.classList.remove("selected"));
    event.currentTarget.classList.add("selected");
    selectedPlanet = planet;
}

function setAutoStatus(mode, planetName) {
    const el = document.getElementById("auto_status");
    el.classList.remove("hidden", "moving", "tracking");
    if (mode === "moving") {
        el.classList.add("moving");
        el.innerHTML = `Moving to ${planetName}<span class="dots"></span>`;
    } else if (mode === "tracking") {
        el.classList.add("tracking");
        el.innerHTML = `Tracking ${planetName}<span class="dots"></span>`;
    } else if (mode === "slewing") {
        el.classList.add("slewing");
        el.innerHTML = `Slewing to coordinates — ${planetName}<span class="dots"></span>`;
    } else {
        el.classList.add("hidden");
    }
}

async function moveToSelectedPlanet() {
    if (!selectedPlanet) {
        alert("No planet selected.");
        return;
    }
    if (isMoving) {
        alert("Already Moving!");
        return;
    }
    setAutoStatus("moving", selectedPlanet.name);
    await fetch("/select_planet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selectedPlanet.name })
    });
}

async function trackSelectedPlanet() {
    if (!selectedPlanet) {
        alert("No planet selected.");
        return;
    }
    if (isMoving) {
        alert("Already Moving!");
        return;
    }
    setAutoStatus("tracking", selectedPlanet.name);
    await fetch("/track_planet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selectedPlanet.name })
    });
}

async function fetchStatus() {
    const response = await fetch("/status");
    const data = await response.json();
    document.getElementById("altitude").textContent = data.altitude;
    document.getElementById("azimuth").textContent = data.azimuth;
    document.getElementById("pulse_delay").textContent = data.pulse_delay;
    isMoving = data.moving;

    if (wasMoving && !data.moving) {
        setAutoStatus("hidden");
    }
    wasMoving = data.moving;

    const moving = data.moving ? "Yes" : "No";
    document.getElementById("moving").textContent = moving;
    const el = document.getElementById("status");
    el.textContent = data.sys_ready ? "System Ready" : "System Arming...";
    el.className = data.sys_ready ? "ready" : "arming";
}


setInterval(fetchStatus, 100);
loadPlanets();
