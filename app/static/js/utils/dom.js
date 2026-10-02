/* Small DOM helpers. */

const SVG_NS = "http://www.w3.org/2000/svg";

export const $ = (id) => document.getElementById(id);

export function svgEl(tag, attrs = {}, parent = null) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [key, value] of Object.entries(attrs)) {
        el.setAttribute(key, value);
    }
    if (parent) parent.appendChild(el);
    return el;
}

// Paints the filled part of a range slider's track (see --fill in components.css).
export function updateRangeFill(input) {
    const min = Number(input.min);
    const max = Number(input.max);
    const pct = ((Number(input.value) - min) / (max - min)) * 100;
    input.style.setProperty("--fill", `${pct}%`);
}
