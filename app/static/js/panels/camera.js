/* 03 Camera: sliders, stream fallback, reticle toggle and HUD overlays. */

import { $, updateRangeFill } from "../utils/dom.js";
import { fixed, formatClock } from "../utils/format.js";

export function renderHud(data) {
    $("hud_az").textContent = fixed(data.azimuth, 2);
    $("hud_el").textContent = fixed(data.altitude, 2);
}

export function renderHudTime(now) {
    $("hud_time").textContent = `${formatClock(now, true)} UTC`;
}

function setupSliders() {
    const brightness = $("brightnessRange");
    const exposure = $("exposureRange");
    const gain = $("gainRange");
    const outputs = [
        [brightness, $("brightnessValue")],
        [exposure, $("exposureValue")],
        [gain, $("gainValue")],
    ];

    // Debounced so dragging a slider doesn't flood the Pi.
    let timeout = null;
    function sendToBackend() {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            fetch("/update_camera", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    brightness: brightness.value,
                    exposure: exposure.value,
                    gain: gain.value,
                }),
            }).catch((error) => console.error("Camera update failed:", error));
        }, 50);
    }

    outputs.forEach(([input, output]) => {
        output.textContent = input.value;
        updateRangeFill(input);
        input.addEventListener("input", () => {
            output.textContent = input.value;
            updateRangeFill(input);
            sendToBackend();
        });
    });
}

export function setupCamera() {
    setupSliders();

    const stream = $("camera-stream");
    stream.addEventListener("error", () => {
        $("no_signal").hidden = false;
    });
    $("camera_retry").addEventListener("click", () => {
        $("no_signal").hidden = true;
        stream.src = `/video_feed?t=${Date.now()}`;
    });

    $("reticle_toggle").addEventListener("click", (event) => {
        const on = $("viewport").classList.toggle("reticle-off") === false;
        event.currentTarget.setAttribute("aria-pressed", on ? "true" : "false");
    });
}
