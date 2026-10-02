/* 02 Manual control: jog pad, stop, pulse delay slider and go-to coordinates. */

import { JOG_HEARTBEAT_MS } from "../config.js";
import { state } from "../state.js";
import { post } from "../core/api.js";
import { restingMode, setMode } from "../core/mode.js";
import { logEvent } from "./log.js";
import { $, updateRangeFill } from "../utils/dom.js";

/* ---------- Jogging ---------- */

// Dead-man: while a jog button is held, tell the Pi every JOG_HEARTBEAT_MS.
// If these stop arriving (Wi-Fi drop, laptop asleep), the Pi stops the mount.
let heartbeatTimer = null;

function startHeartbeat() {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
        fetch("/movement_heartbeat", { method: "POST" }).catch(() => {
            // Lost heartbeats are the point: the Pi stops the jog on its own.
        });
    }, JOG_HEARTBEAT_MS);
}

function stopHeartbeat() {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
}

export async function startJog(direction) {
    if (state.jogDirection) return;
    state.jogDirection = direction;
    document.querySelector(`.jog[data-dir="${direction}"]`)?.classList.add("is-pressed");
    setMode("jogging", direction);
    startHeartbeat();

    const result = await post("/movement_pressed", { action: direction }, `Jog ${direction}`);
    // If the press was rejected and the button is still held, release locally
    // without sending a stop (nothing started moving).
    if (!result.ok && state.jogDirection === direction) {
        state.jogDirection = null;
        stopHeartbeat();
        clearJogHighlight();
        setMode(restingMode());
    }
}

export async function stopJog() {
    if (!state.jogDirection) return;
    const direction = state.jogDirection;
    state.jogDirection = null;
    stopHeartbeat();
    clearJogHighlight();
    if (state.mode === "jogging") setMode(restingMode());
    await post("/movement_unpressed", { action: direction }, `Release ${direction}`);
}

function clearJogHighlight() {
    document.querySelectorAll(".jog.is-pressed").forEach((btn) => btn.classList.remove("is-pressed"));
}

export async function stopAll() {
    state.jogDirection = null;
    stopHeartbeat();
    clearJogHighlight();
    const result = await post("/stop_move_to", undefined, "Stop");
    if (result.ok) {
        logEvent("warn", "Stop command sent. All motion halted.");
        setMode(restingMode());
    }
}

/* ---------- Pulse delay ---------- */

function setSpeedSlider(delay) {
    const slider = $("speed_range");
    slider.value = delay;
    updateRangeFill(slider);
    $("speed_value").textContent = `${delay} ms`;
}

// Keep the slider in sync with the MCU until the user touches it.
export function syncSpeedSlider(pulseDelay) {
    if (!state.speedTouched && pulseDelay) {
        setSpeedSlider(pulseDelay);
    }
}

async function applySpeed() {
    const delay = Number($("speed_range").value);
    const result = await post("/set_pulse", { delay }, "Set pulse delay");
    if (result.ok) {
        logEvent("info", `Pulse delay ${delay} ms requested.`);
    }
}

/* ---------- Go to coordinates ---------- */

// Limits come from the input's min/max attributes (rendered from config.py)
function validateCoordinate(input) {
    const raw = input.value.trim();
    const value = Number(raw);
    const valid = raw !== "" && Number.isFinite(value)
        && value >= Number(input.min) && value <= Number(input.max);
    input.closest(".input-unit").classList.toggle("is-invalid", !valid);
    return valid ? value : null;
}

function rangeMessage(name, input) {
    return `${name} must be between ${input.min} and ${input.max}°.`;
}

async function submitGoto(event) {
    event.preventDefault();
    const errorEl = $("goto_error");
    const azInput = $("move_azimuth");
    const elInput = $("move_altitude");
    const az = validateCoordinate(azInput);
    const el = validateCoordinate(elInput);

    if (az === null || el === null) {
        errorEl.textContent = az === null ? rangeMessage("Azimuth", azInput) : rangeMessage("Elevation", elInput);
        return;
    }
    errorEl.textContent = "";

    const result = await post("/move_to", { azimuth: az, altitude: el }, "Slew");
    if (result.ok) {
        const label = `az ${az.toFixed(2)}° el ${el.toFixed(2)}°`;
        state.commanded = { az, el };
        setMode("slewing", label);
        logEvent("info", `Slewing to ${label}.`);
    }
}

/* ---------- Wiring ---------- */

export function setupManual() {
    // Jog pad: pointer events cover mouse, pen and touch.
    document.querySelectorAll(".jog").forEach((btn) => {
        btn.addEventListener("pointerdown", (event) => {
            if (event.button !== 0) return;
            btn.setPointerCapture(event.pointerId);
            startJog(btn.dataset.dir);
        });
        ["pointerup", "pointercancel", "lostpointercapture"].forEach((type) => {
            btn.addEventListener(type, () => stopJog());
        });
    });
    window.addEventListener("blur", () => stopJog());

    $("stop_btn").addEventListener("click", stopAll);

    const speed = $("speed_range");
    updateRangeFill(speed);
    speed.addEventListener("input", () => {
        state.speedTouched = true;
        $("speed_value").textContent = `${speed.value} ms`;
        updateRangeFill(speed);
    });
    speed.addEventListener("change", applySpeed);

    $("goto_form").addEventListener("submit", submitGoto);
    ["move_azimuth", "move_altitude"].forEach((id) => {
        $(id).addEventListener("input", () => {
            $(id).closest(".input-unit").classList.remove("is-invalid");
            $("goto_error").textContent = "";
        });
    });
}
