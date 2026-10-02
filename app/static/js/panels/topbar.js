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

export function renderClocks(now) {
    $("clock_local").textContent = formatClock(now);
    $("clock_utc").textContent = formatClock(now, true);

    const lon = state.status && state.status.longitude;
    $("clock_lst").textContent = isNumber(lon) ? formatHours(localSiderealHours(now, lon)) : "--:--:--";
}
