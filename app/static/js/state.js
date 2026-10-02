/* Shared UI state. Modules read and write it directly, so keep it flat. */

export const state = {
    status: null,            // last /status payload, null until the first poll lands
    serverOnline: null,      // null until the first poll finishes
    mode: "idle",            // idle | slewing | tracking | calibrating | jogging
    modeTarget: null,
    modeSince: 0,
    commanded: null,         // { az, el } of the current slew target, for the sky view
    planets: [],
    selectedPlanet: null,
    jogDirection: null,
    speedTouched: false,     // stop syncing the speed slider once the user moves it
};
