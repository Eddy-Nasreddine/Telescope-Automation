/* Geometry helpers for the dials and the sky view. */

export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

// Point on a circle using compass bearings (0 = up, clockwise).
export function polar(cx, cy, r, bearingDeg) {
    const rad = (bearingDeg * Math.PI) / 180;
    return [cx + r * Math.sin(rad), cy - r * Math.cos(rad)];
}
