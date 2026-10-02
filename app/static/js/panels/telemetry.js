/* 01 Telemetry: azimuth dial, elevation gauge and the data table. */

import { MIN_ELEVATION } from "../config.js";
import { $, svgEl } from "../utils/dom.js";
import { fixed, formatCoord, isNumber, signed } from "../utils/format.js";
import { clamp, polar } from "../utils/math.js";

/* ---------- Azimuth dial ---------- */

let azNeedle = null;
let azNeedleAngle = 0;

function buildAzDial() {
    const svg = $("az_dial");
    const c = 60;
    svgEl("circle", { cx: c, cy: c, r: 54, class: "dial-face" }, svg);

    for (let deg = 0; deg < 360; deg += 10) {
        const major = deg % 30 === 0;
        const [x1, y1] = polar(c, c, 54, deg);
        const [x2, y2] = polar(c, c, major ? 46 : 50, deg);
        svgEl("line", { x1, y1, x2, y2, class: major ? "dial-tick major" : "dial-tick" }, svg);
    }

    [["N", 0], ["E", 90], ["S", 180], ["W", 270]].forEach(([label, deg]) => {
        const [x, y] = polar(c, c, 37, deg);
        const text = svgEl("text", { x, y, class: label === "N" ? "dial-label north" : "dial-label" }, svg);
        text.textContent = label;
    });

    azNeedle = svgEl("g", { class: "dial-needle" }, svg);
    azNeedle.style.transformOrigin = `${c}px ${c}px`;
    svgEl("line", { x1: c, y1: c + 10, x2: c, y2: 14 }, azNeedle);
    svgEl("path", { d: `M${c} 9 l-4 8 h8 z`, class: "dial-needle-tip" }, azNeedle);
    svgEl("circle", { cx: c, cy: c, r: 4, class: "dial-hub" }, svg);
}

function updateAzDial(az) {
    if (!azNeedle || !isNumber(az)) return;
    // Unwrap so the needle takes the short way across 0°/360°.
    const delta = ((((az - azNeedleAngle) % 360) + 540) % 360) - 180;
    azNeedleAngle += delta;
    azNeedle.style.transform = `rotate(${azNeedleAngle}deg)`;
}

/* ---------- Elevation gauge ---------- */

let elNeedle = null;
const EL_PIVOT = [16, 104];
const EL_RADIUS = 88;

// Elevation gauge point: 0° = horizon (right), 90° = zenith (up).
function elPoint(r, elDeg) {
    const rad = (elDeg * Math.PI) / 180;
    return [EL_PIVOT[0] + r * Math.cos(rad), EL_PIVOT[1] - r * Math.sin(rad)];
}

function buildElGauge() {
    const svg = $("el_gauge");
    const [px, py] = EL_PIVOT;
    const r = EL_RADIUS;

    svgEl("path", { d: `M${px} ${py} L${px + r} ${py} A${r} ${r} 0 0 0 ${px} ${py - r} Z`, class: "dial-face" }, svg);

    // Below-minimum zone (0° to MIN_ELEVATION).
    const zr = r - 4;
    const [zx, zy] = elPoint(zr, MIN_ELEVATION);
    svgEl("path", { d: `M${px + zr} ${py} A${zr} ${zr} 0 0 0 ${zx} ${zy}`, class: "dial-zone" }, svg);

    for (let deg = 0; deg <= 90; deg += 5) {
        const major = deg % 15 === 0;
        const [x1, y1] = elPoint(r, deg);
        const [x2, y2] = elPoint(major ? r - 9 : r - 5, deg);
        svgEl("line", { x1, y1, x2, y2, class: major ? "dial-tick major" : "dial-tick" }, svg);
    }

    [0, 45, 90].forEach((deg) => {
        const [x, y] = elPoint(r - 18, deg);
        const text = svgEl("text", { x, y, class: "dial-label" }, svg);
        text.textContent = `${deg}°`;
    });

    elNeedle = svgEl("g", { class: "dial-needle" }, svg);
    elNeedle.style.transformOrigin = `${px}px ${py}px`;
    svgEl("line", { x1: px, y1: py, x2: px + r - 12, y2: py }, elNeedle);
    svgEl("path", { d: `M${px + r - 6} ${py} l-8 -4 v8 z`, class: "dial-needle-tip" }, elNeedle);
    svgEl("circle", { cx: px, cy: py, r: 4, class: "dial-hub" }, svg);
}

function updateElGauge(el) {
    if (!elNeedle || !isNumber(el)) return;
    elNeedle.style.transform = `rotate(${-clamp(el, 0, 90)}deg)`;
}

/* ---------- Readouts ---------- */

function setStatusText(id, text, cls) {
    const el = $(id);
    el.textContent = text;
    el.className = cls || "";
}

export function renderTelemetry(data) {
    $("azimuth").textContent = fixed(data.azimuth, 3);
    $("elevation").textContent = fixed(data.altitude, 3);
    $("azimuth_error").textContent = signed(data.azimuth_error, 3);
    $("elevation_error").textContent = signed(data.elevation_error, 3);
    $("pulse_delay").textContent = data.pulse_delay ? `${data.pulse_delay} ms` : "—";
    $("latitude").textContent = formatCoord(data.latitude, "N", "S");
    $("longitude").textContent = formatCoord(data.longitude, "E", "W");
    setStatusText("moving", data.moving ? "Yes" : "No", data.moving ? "is-active" : "");
    setStatusText("calibrating", data.calibrating ? "Yes" : "No", data.calibrating ? "is-active" : "");
    setStatusText("mcu_status", data.sys_ready ? "Connected" : "Waiting for UART…", data.sys_ready ? "is-ok" : "is-wait");
    setStatusText("gps_status", data.gps_ready ? "Fix acquired" : "Waiting for fix…", data.gps_ready ? "is-ok" : "is-wait");

    updateAzDial(data.azimuth);
    updateElGauge(data.altitude);
}

export function setupTelemetry() {
    buildAzDial();
    buildElGauge();
}
