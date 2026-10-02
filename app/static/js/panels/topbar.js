/* Top bar: link lamps and the local / UTC / sidereal clocks. */

import { state } from "../state.js";
import { $ } from "../utils/dom.js";
import { formatClock, formatHours, isNumber } from "../utils/format.js";

// lampState: ok | wait | bad | active | off (styled in topbar.css)
export function setLamp(id, lampState) {
    $(id).dataset.state = lampState;
}

export function renderLamps(data) {
    setLamp("lamp_mcu", data.sys_ready ? "ok" : "wait");
    setLamp("lamp_gps", data.gps_ready ? "ok" : "wait");
    setLamp("lamp_motion", data.moving ? "active" : "off");
}

// Approximate local sidereal time in hours (good to about a second).
function localSiderealHours(date, longitudeDeg) {
    const julianDate = date.getTime() / 86400000 + 2440587.5;
    const daysSinceJ2000 = julianDate - 2451545.0;
    const gmst = 18.697374558 + 24.06570982441908 * daysSinceJ2000;
    return ((((gmst + longitudeDeg / 15) % 24) + 24) % 24);
}

// The Pi has no internet outside, so send it the laptop's clock. It's only used
// until the GPS provides time. Resent every minute so a restarted server picks it up.
const TIME_SYNC_MS = 60000;

function sendLaptopTime() {
    return fetch("/sync_time", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ epoch_ms: Date.now() }),
    }).catch(() => {
        // Server unreachable; the next attempt will retry.
    });
}

// Resolves once the first sync has been answered (or failed), so callers can
// wait for it before asking the Pi for planet positions.
export function startTimeSync() {
    setInterval(sendLaptopTime, TIME_SYNC_MS);
    return sendLaptopTime();
}

export function renderClocks(now) {
    $("clock_local").textContent = formatClock(now);
    $("clock_utc").textContent = formatClock(now, true);

    const lon = state.status && state.status.longitude;
    $("clock_lst").textContent = isNumber(lon) ? formatHours(localSiderealHours(now, lon)) : "--:--:--";
}
