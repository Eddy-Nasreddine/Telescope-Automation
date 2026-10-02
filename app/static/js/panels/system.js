/* 07 System: calibration, reset origin and the test endpoint. */

import { post } from "../core/api.js";
import { setMode } from "../core/mode.js";
import { logEvent } from "./log.js";
import { $ } from "../utils/dom.js";

export function showCalibrationCallout(visible) {
    $("calibration_callout").hidden = !visible;
}

// The "calibration started" log line comes from status.js when /status flips,
// so it's written once even if calibration was started from another device.
async function startCalibration() {
    const result = await post("/startCalibration", undefined, "Calibrate");
    if (result.ok) {
        setMode("calibrating");
        showCalibrationCallout(true);
    }
}

async function finishCalibration() {
    await post("/finishCalibration", undefined, "Finish calibration");
}

// Reset origin re-defines where the mount thinks it is, so it takes two clicks.
let resetArmTimer = null;

async function resetOrigin() {
    const btn = $("reset_origin_btn");
    if (!btn.classList.contains("is-armed")) {
        btn.classList.add("is-armed");
        btn.textContent = "Confirm reset?";
        resetArmTimer = setTimeout(disarmReset, 3000);
        return;
    }
    disarmReset();
    const result = await post("/resetOrigin", undefined, "Reset origin");
    if (result.ok) {
        logEvent("warn", "Origin reset. Position is now az 90°, el 90°.");
    }
}

function disarmReset() {
    clearTimeout(resetArmTimer);
    const btn = $("reset_origin_btn");
    btn.classList.remove("is-armed");
    btn.textContent = "Reset origin";
}

async function runTest() {
    const result = await post("/test", undefined, "Test");
    if (result.ok) logEvent("info", "Test endpoint called. See the server console.");
}

export function setupSystem() {
    $("calibrate_btn").addEventListener("click", startCalibration);
    $("finish_calibration_btn").addEventListener("click", finishCalibration);
    $("reset_origin_btn").addEventListener("click", resetOrigin);
    $("test_btn").addEventListener("click", runTest);
}
