/* Polls /status, fans the data out to the panels and logs state changes. */

import { SLEW_START_TIMEOUT_MS, STATUS_POLL_MS, STATUS_RETRY_MS } from "../config.js";
import { state } from "../state.js";
import { restingMode, setMode } from "./mode.js";
import { renderHud, syncCameraHealth } from "../panels/camera.js";
import { logEvent, warnUser } from "../panels/log.js";
import { syncSpeedSlider } from "../panels/manual.js";
import { moveSkyScope } from "../panels/sky.js";
import { showCalibrationCallout } from "../panels/system.js";
import { renderTelemetry } from "../panels/telemetry.js";
import { renderLamps, setLamp } from "../panels/topbar.js";
import { fixed, formatCoord, signed } from "../utils/format.js";

function setServerOnline(online) {
    if (state.serverOnline === online) return;
    const first = state.serverOnline === null;
    state.serverOnline = online;
    setLamp("lamp_server", online ? "ok" : "bad");

    if (online) {
        logEvent("ok", first ? "Connected to the telescope server." : "Reconnected to the telescope server.");
    } else {
        warnUser("Lost connection to the telescope server. Retrying…", "err");
        setLamp("lamp_mcu", "off");
        setLamp("lamp_gps", "off");
        setLamp("lamp_motion", "off");
    }
}

function render(data) {
    renderTelemetry(data);
    renderLamps(data);
    renderHud(data);
    moveSkyScope(data.altitude, data.azimuth);
    syncSpeedSlider(data.pulse_delay);
    syncCameraHealth(data.camera_ok);
}

function logLinkChanges(prev, data, first) {
    if (data.sys_ready && !prev.sys_ready) {
        logEvent("ok", "MCU link established over UART.");
    } else if (!data.sys_ready && prev.sys_ready) {
        warnUser("Lost the MCU link. Check the UART connection.", "err");
    } else if (first && !data.sys_ready) {
        logEvent("info", "Waiting for the MCU handshake…");
    }

    if (data.gps_ready && !prev.gps_ready) {
        logEvent("ok", `GPS fix acquired: ${formatCoord(data.latitude, "N", "S")}, ${formatCoord(data.longitude, "E", "W")}.`);
    } else if (!data.gps_ready && prev.gps_ready) {
        warnUser("GPS fix lost. Using the last known position.");
    } else if (first && !data.gps_ready) {
        logEvent("info", "Waiting for a GPS fix…");
    }

    if (data.pulse_delay && prev.pulse_delay && data.pulse_delay !== prev.pulse_delay) {
        logEvent("ok", `MCU pulse delay is now ${data.pulse_delay} ms.`);
    }
}

function updateMode(prev, data, first) {
    if (data.calibrating && !prev.calibrating) {
        setMode("calibrating");
        showCalibrationCallout(true);
        if (!first) logEvent("info", "Calibration started. Slewing to Polaris.");
    } else if (!data.calibrating && prev.calibrating) {
        showCalibrationCallout(false);
        setMode("idle");
        logEvent("ok", `Calibration finished. Offset az ${signed(data.azimuth_error, 3)}°, el ${signed(data.elevation_error, 3)}°.`);
    }

    // Tracking runs on the Pi, so /status is the source of truth for it
    if (data.tracking && state.mode !== "jogging"
            && (state.mode !== "tracking" || state.modeTarget !== data.tracking)) {
        setMode("tracking", data.tracking);
    } else if (!data.tracking && prev.tracking) {
        logEvent("info", `Tracking ${prev.tracking} stopped.`);
        if (state.mode === "tracking") setMode(restingMode());
    }

    if (prev.moving && !data.moving && !data.calibrating && !data.tracking && state.mode !== "jogging") {
        if (state.mode === "slewing") {
            logEvent("ok", `Arrived at ${state.modeTarget || "target"}. Final position az ${fixed(data.azimuth, 2)}°, el ${fixed(data.altitude, 2)}°.`);
        }
        if (state.mode !== "idle") setMode("idle");
    }

    // A slew that never produced motion (e.g. already on target) shouldn't hang.
    if (state.mode === "slewing" && !data.moving && !prev.moving && Date.now() - state.modeSince > SLEW_START_TIMEOUT_MS) {
        setMode(restingMode());
    }

    // Calibration can outlive a stop or a jog; keep the mode honest.
    if (data.calibrating && state.mode === "idle") {
        setMode("calibrating");
    }
}

function applyStatus(data) {
    const prev = state.status || {};
    const first = state.status === null;
    state.status = data;

    render(data);
    logLinkChanges(prev, data, first);
    updateMode(prev, data, first);
}

async function pollStatus() {
    try {
        const response = await fetch("/status", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        setServerOnline(true);
        applyStatus(data);
    } catch (error) {
        setServerOnline(false);
    } finally {
        setTimeout(pollStatus, state.serverOnline ? STATUS_POLL_MS : STATUS_RETRY_MS);
    }
}

export function startStatusPolling() {
    pollStatus();
}
