/* What the telescope is doing right now (shown in the mode pill and camera HUD). */

import { state } from "../state.js";
import { $ } from "../utils/dom.js";

const listeners = [];

// Lets panels react to mode changes without this module importing them.
export function onModeChange(listener) {
    listeners.push(listener);
}

function modeText(mode, target) {
    switch (mode) {
        case "slewing": return target ? `Slewing → ${target}` : "Slewing";
        case "tracking": return target ? `Tracking ${target}` : "Tracking";
        case "calibrating": return "Calibrating · Polaris";
        case "jogging": return target ? `Jogging ${target}` : "Jogging";
        default: return "Idle";
    }
}

export function setMode(mode, target = null) {
    state.mode = mode;
    state.modeTarget = target;
    state.modeSince = Date.now();
    if (mode === "idle" || mode === "calibrating") {
        state.commanded = null;
    }

    const text = modeText(mode, target);
    $("mode_pill").dataset.mode = mode;
    $("mode_text").textContent = text;
    $("hud_mode").textContent = text;

    listeners.forEach((listener) => listener(mode, target));
}

// The mode to fall back to when nothing is actively moving.
export function restingMode() {
    return state.status && state.status.calibrating ? "calibrating" : "idle";
}
