/* Shared constants for the front end. */

export const STATUS_POLL_MS = 100;
export const STATUS_RETRY_MS = 1000;
export const PLANET_REFRESH_MS = 30000;
export const SLEW_START_TIMEOUT_MS = 4000;
export const CAMERA_CONNECT_TIMEOUT_MS = 10000; // no first frame by then = no signal
export const MIN_ELEVATION = 25; // must match the visibility cutoff in app.py /planets
export const LOG_LIMIT = 200;
export const THEME_KEY = "telescope.theme";

export const PLANET_COLORS = {
    Moon: "#e9e4d4",
    Mercury: "#b9b1a5",
    Venus: "#f3d9a4",
    Mars: "#e8836b",
    Jupiter: "#e6b98a",
    Saturn: "#f0d28c",
    Uranus: "#9fe3e6",
    Neptune: "#7d9cf0",
};
