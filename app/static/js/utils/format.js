/* Number and time formatting for readouts. */

const pad2 = (n) => String(n).padStart(2, "0");

export function formatClock(date, utc = false) {
    const h = utc ? date.getUTCHours() : date.getHours();
    const m = utc ? date.getUTCMinutes() : date.getMinutes();
    const s = utc ? date.getUTCSeconds() : date.getSeconds();
    return `${pad2(h)}:${pad2(m)}:${pad2(s)}`;
}

export function formatHours(hours) {
    const totalSeconds = Math.floor(hours * 3600);
    const h = Math.floor(totalSeconds / 3600) % 24;
    const m = Math.floor(totalSeconds / 60) % 60;
    const s = totalSeconds % 60;
    return `${pad2(h)}:${pad2(m)}:${pad2(s)}`;
}

export function isNumber(value) {
    return typeof value === "number" && Number.isFinite(value);
}

export function fixed(value, digits) {
    return isNumber(value) ? value.toFixed(digits) : "—";
}

export function signed(value, digits) {
    if (!isNumber(value)) return "—";
    return (value >= 0 ? "+" : "") + value.toFixed(digits);
}

export function formatCoord(value, positive, negative) {
    if (!isNumber(value)) return "—";
    return `${Math.abs(value).toFixed(5)}° ${value >= 0 ? positive : negative}`;
}
