/* Cosmos / night vision theme switch and the background starfield. */

import { THEME_KEY } from "../config.js";
import { logEvent } from "../panels/log.js";
import { $ } from "../utils/dom.js";

function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    $("night_toggle").setAttribute("aria-pressed", theme === "night" ? "true" : "false");
    try {
        localStorage.setItem(THEME_KEY, theme);
    } catch (_) {
        // Storage unavailable; the theme just won't persist.
    }
    drawStarfield();
}

export function toggleTheme() {
    const next = document.documentElement.dataset.theme === "night" ? "cosmos" : "night";
    setTheme(next);
    logEvent("info", next === "night" ? "Night vision mode on." : "Night vision mode off.");
}

function drawStarfield() {
    const canvas = $("starfield");
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const width = window.innerWidth;
    const height = window.innerHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const rgb = getComputedStyle(document.documentElement).getPropertyValue("--star-rgb").trim() || "236, 230, 216";
    let seed = 42;
    const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    const count = Math.round((width * height) / 4200);

    for (let i = 0; i < count; i++) {
        const x = rand() * width;
        const y = rand() * height;
        const r = rand() < 0.93 ? 0.3 + rand() * 0.6 : 0.9 + rand() * 0.7;
        ctx.fillStyle = `rgba(${rgb}, ${(0.12 + rand() * 0.55).toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
    }
}

export function setupTheme() {
    let savedTheme = "cosmos";
    try {
        savedTheme = localStorage.getItem(THEME_KEY) || "cosmos";
    } catch (_) {
        // Storage unavailable; use the default theme.
    }
    setTheme(savedTheme);

    $("night_toggle").addEventListener("click", toggleTheme);

    let resizeTimer = null;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(drawStarfield, 150);
    });
}
