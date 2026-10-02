/* Entry point: builds each panel, wires shortcuts and starts the timers. */

import { setupKeyboard } from "./core/keyboard.js";
import { startStatusPolling } from "./core/status.js";
import { setupTheme } from "./core/theme.js";
import { renderHudTime, setupCamera } from "./panels/camera.js";
import { logEvent, setupLog } from "./panels/log.js";
import { setupManual } from "./panels/manual.js";
import { setupSky } from "./panels/sky.js";
import { setupSystem } from "./panels/system.js";
import { selectPlanet, setupTargets, startPlanetRefresh } from "./panels/targets.js";
import { setupTelemetry } from "./panels/telemetry.js";
import { renderClocks } from "./panels/topbar.js";

function tickClocks() {
    const now = new Date();
    renderClocks(now);
    renderHudTime(now);
}

function init() {
    setupTheme();
    setupLog();
    setupTelemetry();
    setupManual();
    setupCamera();
    setupSky({ onSelectPlanet: selectPlanet });
    setupTargets();
    setupSystem();
    setupKeyboard();

    logEvent("info", "Console ready.");
    tickClocks();
    setInterval(tickClocks, 1000);
    startStatusPolling();
    startPlanetRefresh();
}

// Module scripts run after the HTML is parsed, so the DOM is ready here.
init();
