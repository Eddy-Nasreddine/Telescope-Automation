/* 05 Sky view: zenith at the centre, horizon at the edge, north up, east right. */

import { MIN_ELEVATION, PLANET_COLORS } from "../config.js";
import { state } from "../state.js";
import { onModeChange } from "../core/mode.js";
import { $, svgEl } from "../utils/dom.js";
import { fixed, isNumber } from "../utils/format.js";
import { clamp, polar } from "../utils/math.js";

const SKY = { cx: 150, cy: 150, r: 124 };
let planetLayer = null;
let commandedLayer = null;
let scope = null;
let onPlanetClick = () => {};

function skyPoint(altDeg, azDeg) {
    const r = (SKY.r * (90 - clamp(altDeg, 0, 90))) / 90;
    return polar(SKY.cx, SKY.cy, r, azDeg);
}

function buildDome() {
    const svg = $("sky_dome");
    const { cx, cy, r } = SKY;

    svgEl("circle", { cx, cy, r, class: "sky-disc" }, svg);

    // Decorative background stars, fixed seed so they don't jump around.
    let seed = 7;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 70; i++) {
        const dist = Math.sqrt(rand()) * (r - 4);
        const [x, y] = polar(cx, cy, dist, rand() * 360);
        svgEl("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: (0.3 + rand() * 0.8).toFixed(2), class: "sky-star", opacity: (0.15 + rand() * 0.5).toFixed(2) }, svg);
    }

    for (let az = 0; az < 360; az += 30) {
        const [x, y] = polar(cx, cy, r, az);
        svgEl("line", { x1: cx, y1: cy, x2: x, y2: y, class: "sky-spoke" }, svg);
    }
    [30, 60].forEach((alt) => {
        const ringR = (r * (90 - alt)) / 90;
        svgEl("circle", { cx, cy, r: ringR, class: "sky-ring" }, svg);
        const label = svgEl("text", { x: cx + 3, y: cy - ringR - 3, class: "sky-ring-label" }, svg);
        label.textContent = `${alt}°`;
    });
    svgEl("circle", { cx, cy, r: (r * (90 - MIN_ELEVATION)) / 90, class: "sky-ring-min" }, svg);

    [["N", 0], ["E", 90], ["S", 180], ["W", 270]].forEach(([label, az]) => {
        const [x, y] = polar(cx, cy, r + 13, az);
        const text = svgEl("text", { x, y, class: label === "N" ? "sky-label north" : "sky-label" }, svg);
        text.textContent = label;
    });

    // Layer order = draw order: planets, then the commanded target, then the scope on top.
    planetLayer = svgEl("g", {}, svg);
    commandedLayer = svgEl("g", {}, svg);

    scope = svgEl("g", { class: "sky-scope" }, svg);
    svgEl("circle", { cx: 0, cy: 0, r: 10, class: "scope-halo" }, scope);
    svgEl("circle", { cx: 0, cy: 0, r: 10 }, scope);
    svgEl("path", { d: "M0 -16v-5M0 16v5M-16 0h-5M16 0h5" }, scope);
    moveSkyScope(90, 0);
}

export function moveSkyScope(el, az) {
    if (!scope || !isNumber(el) || !isNumber(az)) return;
    const [x, y] = skyPoint(el, az);
    scope.setAttribute("transform", `translate(${x.toFixed(2)} ${y.toFixed(2)})`);
}

export function drawSkyPlanets() {
    if (!planetLayer) return;
    planetLayer.innerHTML = "";

    state.planets.forEach((planet) => {
        if (!isNumber(planet.altitude) || planet.altitude < 0) return;
        const [x, y] = skyPoint(planet.altitude, planet.azimuth);
        const selected = state.selectedPlanet && state.selectedPlanet.name === planet.name;

        const g = svgEl("g", { class: "sky-planet" }, planetLayer);
        g.classList.toggle("is-low", !planet.visible);
        g.classList.toggle("is-selected", Boolean(selected));
        svgEl("circle", { cx: x, cy: y, r: 9, class: "select-ring" }, g);
        svgEl("circle", { cx: x, cy: y, r: planet.name === "Moon" ? 6 : 4.5, fill: PLANET_COLORS[planet.name] || "#ece6d8", class: "body" }, g);
        const label = svgEl("text", { x: x + 9, y: y + 3 }, g);
        label.textContent = planet.name;

        const title = svgEl("title", {}, g);
        title.textContent = `${planet.name}: alt ${fixed(planet.altitude, 1)}°, az ${fixed(planet.azimuth, 1)}°`;

        g.addEventListener("click", () => onPlanetClick(planet));
    });
}

// Amber crosshair on the slew target; cleared when the mode goes idle.
function drawCommanded() {
    if (!commandedLayer) return;
    commandedLayer.innerHTML = "";
    if (!state.commanded) return;
    const [x, y] = skyPoint(state.commanded.el, state.commanded.az);
    svgEl("circle", { cx: x, cy: y, r: 7, class: "sky-target" }, commandedLayer);
    svgEl("path", { d: `M${x - 11} ${y}h4M${x + 7} ${y}h4M${x} ${y - 11}v4M${x} ${y + 7}v4`, class: "sky-target" }, commandedLayer);
}

// onSelectPlanet is passed in (rather than imported) so this panel doesn't depend on targets.js.
export function setupSky({ onSelectPlanet }) {
    onPlanetClick = onSelectPlanet;
    buildDome();
    onModeChange(drawCommanded);
}
