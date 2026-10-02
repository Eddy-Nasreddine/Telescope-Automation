/* 04 Event log, plus toast pop-ups for problems the user should notice. */

import { LOG_LIMIT } from "../config.js";
import { $ } from "../utils/dom.js";
import { formatClock } from "../utils/format.js";

const LOG_TAGS = { info: "INFO", ok: "OK", warn: "WARN", err: "ERR" };

// level: info | ok | warn | err
export function logEvent(level, message) {
    const list = $("event_log");
    const nearBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 24;

    list.querySelector(".log-empty")?.remove();

    const entry = document.createElement("li");
    entry.className = `log-entry log-${level}`;

    const time = document.createElement("time");
    time.textContent = formatClock(new Date());
    const tag = document.createElement("span");
    tag.className = "log-tag";
    tag.textContent = LOG_TAGS[level] || "INFO";
    const msg = document.createElement("span");
    msg.className = "log-msg";
    msg.textContent = message;

    entry.append(time, tag, msg);
    list.appendChild(entry);

    while (list.children.length > LOG_LIMIT) {
        list.firstElementChild.remove();
    }
    // Only follow new entries if the user hasn't scrolled up to read older ones.
    if (nearBottom) {
        list.scrollTop = list.scrollHeight;
    }
}

function clearLog() {
    const list = $("event_log");
    list.innerHTML = "";
    const empty = document.createElement("li");
    empty.className = "log-empty";
    empty.textContent = "Log cleared.";
    list.appendChild(empty);
}

export function toast(level, message) {
    const stack = $("toast_stack");
    const el = document.createElement("div");
    el.className = `toast toast-${level}`;
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => {
        el.classList.add("is-leaving");
        setTimeout(() => el.remove(), 300);
    }, 4000);
}

// A user-facing problem: goes to the log and pops a toast.
export function warnUser(message, level = "warn") {
    logEvent(level, message);
    toast(level, message);
}

export function setupLog() {
    $("log_clear").addEventListener("click", clearLog);
}
