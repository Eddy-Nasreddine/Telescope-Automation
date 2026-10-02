/* Keyboard shortcuts: arrows jog while held, Esc stops everything, N toggles night vision. */

import { state } from "../state.js";
import { startJog, stopAll, stopJog } from "../panels/manual.js";
import { toggleTheme } from "./theme.js";

const KEY_DIRECTIONS = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right" };

function isTypingTarget(el) {
    return el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
}

export function setupKeyboard() {
    document.addEventListener("keydown", (event) => {
        // Esc always works, even while typing in a field.
        if (event.key === "Escape") {
            event.preventDefault();
            stopAll();
            return;
        }
        if (isTypingTarget(document.activeElement) || event.ctrlKey || event.metaKey || event.altKey) return;

        const direction = KEY_DIRECTIONS[event.key];
        if (direction) {
            event.preventDefault();
            if (!event.repeat) startJog(direction);
        } else if (event.key === "n" || event.key === "N") {
            toggleTheme();
        }
    });

    document.addEventListener("keyup", (event) => {
        if (KEY_DIRECTIONS[event.key] && state.jogDirection === KEY_DIRECTIONS[event.key]) {
            stopJog();
        }
    });
}
