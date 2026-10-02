/* 03 Camera: stream state, sliders, reticle toggle and HUD overlays. */

import { CAMERA_CONNECT_TIMEOUT_MS } from "../config.js";
import { logEvent } from "./log.js";
import { setLamp } from "./topbar.js";
import { $, updateRangeFill } from "../utils/dom.js";
import { fixed, formatClock } from "../utils/format.js";

/* ---------- Stream state: connecting -> live | offline ---------- */

const CAMERA_STATES = {
    connecting: {
        status: "Connecting",
        title: "Connecting to camera",
        sub: "Waiting for the first frame…",
        lamp: "wait",
    },
    live: {
        status: "Live · cam 0",
        title: "",
        sub: "",
        lamp: "ok",
    },
    offline: {
        status: "No signal · cam 0",
        title: "No camera signal",
        sub: "The camera isn't connected or isn't sending frames. Check the USB cable, then retry.",
        lamp: "bad",
    },
};

let cameraState = null;
let connectTimer = null;
let frameCheck = null;

function setCameraState(next) {
    if (cameraState === next) return;
    const prev = cameraState;
    cameraState = next;

    const view = CAMERA_STATES[next];
    $("viewport").dataset.camera = next;
    $("camera_status").textContent = view.status;
    $("camera_overlay_title").textContent = view.title;
    $("camera_overlay_sub").textContent = view.sub;
    $("camera_controls").disabled = next !== "live";
    setLamp("lamp_camera", view.lamp);

    if (next === "live") {
        logEvent("ok", "Camera stream live.");
    } else if (next === "offline") {
        logEvent("warn", prev === "live" ? "Camera stream lost." : "No camera signal. Check the USB camera, then retry.");
    }
}

function stopWaiting() {
    clearTimeout(connectTimer);
    clearInterval(frameCheck);
}

function markLive() {
    stopWaiting();
    setCameraState("live");
}

function markOffline() {
    stopWaiting();
    // Drop the request so a stream that never sends frames doesn't hold a server thread.
    $("camera-stream").removeAttribute("src");
    setCameraState("offline");
}

function connectStream() {
    const stream = $("camera-stream");
    stopWaiting();
    setCameraState("connecting");
    stream.src = `/video_feed?t=${Date.now()}`;

    // An MJPEG stream has a non-zero size once its first frame decodes; this catches
    // browsers that don't fire "load" for multipart streams.
    frameCheck = setInterval(() => {
        if (stream.naturalWidth > 0) markLive();
    }, 250);
    connectTimer = setTimeout(() => {
        if (cameraState === "connecting") markOffline();
    }, CAMERA_CONNECT_TIMEOUT_MS);
}

/* ---------- HUD ---------- */

export function renderHud(data) {
    $("hud_az").textContent = fixed(data.azimuth, 2);
    $("hud_el").textContent = fixed(data.altitude, 2);
}

export function renderHudTime(now) {
    $("hud_time").textContent = `${formatClock(now, true)} UTC`;
}

/* ---------- Sliders ---------- */

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

/* ---------- Wiring ---------- */

export function setupCamera() {
    setupSliders();

    // Listeners go on before the first src is set, so a fast failure can't be missed.
    const stream = $("camera-stream");
    stream.addEventListener("load", markLive);
    stream.addEventListener("error", () => {
        if (cameraState !== "offline") markOffline();
    });
    $("camera_retry").addEventListener("click", () => {
        logEvent("info", "Retrying camera connection…");
        connectStream();
    });
    connectStream();

    $("reticle_toggle").addEventListener("click", (event) => {
        const on = $("viewport").classList.toggle("reticle-off") === false;
        event.currentTarget.setAttribute("aria-pressed", on ? "true" : "false");
    });
}
