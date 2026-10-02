/* 06 Targets: planet cards, selection and the Go to / Track actions. */

import { MIN_ELEVATION, PLANET_REFRESH_MS } from "../config.js";
import { state } from "../state.js";
import { post } from "../core/api.js";
import { setMode } from "../core/mode.js";
import { logEvent, toast, warnUser } from "./log.js";
import { drawSkyPlanets } from "./sky.js";
import { $ } from "../utils/dom.js";
import { fixed, formatClock, isNumber } from "../utils/format.js";

/* ---------- Loading + rendering ---------- */

async function loadPlanets() {
    try {
        const response = await fetch("/planets", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        state.planets = await response.json();
    } catch (error) {
        console.error("Planet refresh failed:", error);
        if (!state.planets.length) {
            $("planet_list").innerHTML = '<p class="target-empty">Couldn\'t load targets. Retrying shortly.</p>';
        }
        return;
    }

    // Keep the selection fresh, or drop it if it sank below the limit.
    if (state.selectedPlanet) {
        const fresh = state.planets.find((p) => p.name === state.selectedPlanet.name);
        if (fresh && fresh.visible) {
            state.selectedPlanet = fresh;
        } else {
            logEvent("warn", `${state.selectedPlanet.name} dropped below ${MIN_ELEVATION}°. Selection cleared.`);
            state.selectedPlanet = null;
        }
    }

    $("planets_updated").textContent = `upd ${formatClock(new Date()).slice(0, 5)}`;
    renderPlanetCards();
    drawSkyPlanets();
    updateSelectedLabel();
}

function renderPlanetCards() {
    const container = $("planet_list");
    container.innerHTML = "";

    state.planets.forEach((planet) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "target-card";
        const selected = state.selectedPlanet && state.selectedPlanet.name === planet.name;
        card.classList.toggle("is-selected", Boolean(selected));
        card.classList.toggle("is-unavailable", !planet.visible);
        card.setAttribute("aria-pressed", selected ? "true" : "false");
        if (!planet.visible) card.setAttribute("aria-disabled", "true");

        const alt = fixed(planet.altitude, 1);
        const az = fixed(planet.azimuth, 1);
        card.title = planet.visible
            ? `${planet.name}: alt ${alt}°, az ${az}°`
            : `${planet.name}: alt ${alt}°, below the ${MIN_ELEVATION}° minimum`;

        const flag = document.createElement("span");
        flag.className = "target-flag";
        const img = document.createElement("img");
        img.src = `/static/images/${planet.image}`;
        img.alt = "";
        const name = document.createElement("span");
        name.className = "target-name";
        name.textContent = planet.name;
        const altEl = document.createElement("span");
        altEl.className = "target-alt";
        altEl.textContent = isNumber(planet.altitude) ? `alt ${alt}°` : "";

        card.append(flag, img, name, altEl);
        card.addEventListener("click", () => selectPlanet(planet));
        container.appendChild(card);
    });
}

function updateSelectedLabel() {
    $("selected_target").textContent = state.selectedPlanet ? state.selectedPlanet.name : "None";
}

// Used by both the cards and the sky view.
export function selectPlanet(planet) {
    if (!planet.visible) {
        toast("warn", `${planet.name} is at ${fixed(planet.altitude, 1)}°, below the ${MIN_ELEVATION}° minimum.`);
        return;
    }
    state.selectedPlanet = planet;
    renderPlanetCards();
    drawSkyPlanets();
    updateSelectedLabel();
}

/* ---------- Actions ---------- */

// Shared guard for target actions; returns the planet or null.
function readyForTargetAction() {
    const planet = state.selectedPlanet;
    if (!planet) {
        warnUser("Select a target first.");
        return null;
    }
    if (state.status && state.status.calibrating) {
        warnUser("Finish calibration before moving to a target.");
        return null;
    }
    if (state.status && state.status.moving) {
        warnUser("The telescope is already moving.");
        return null;
    }
    return planet;
}

async function gotoSelected() {
    const planet = readyForTargetAction();
    if (!planet) return;
    const result = await post("/select_planet", { name: planet.name }, `Go to ${planet.name}`);
    if (result.ok) {
        state.commanded = { az: planet.azimuth, el: planet.altitude };
        setMode("slewing", planet.name);
        logEvent("info", `Slewing to ${planet.name} (alt ${fixed(planet.altitude, 1)}°, az ${fixed(planet.azimuth, 1)}°).`);
    }
}

async function trackSelected() {
    const planet = readyForTargetAction();
    if (!planet) return;
    const result = await post("/track_planet", { name: planet.name }, `Track ${planet.name}`);
    if (result.ok) {
        setMode("tracking", planet.name);
        logEvent("info", `Tracking ${planet.name}.`);
    }
}

/* ---------- Wiring ---------- */

export function setupTargets() {
    $("goto_target_btn").addEventListener("click", gotoSelected);
    $("track_target_btn").addEventListener("click", trackSelected);
}

export function startPlanetRefresh() {
    loadPlanets();
    setInterval(loadPlanets, PLANET_REFRESH_MS);
}
