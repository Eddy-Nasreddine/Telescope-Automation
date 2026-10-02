/* POST helper for the Flask backend. */

import { warnUser } from "../panels/log.js";

// Failures are logged under `label` and surfaced as a toast;
// callers only need to check `result.ok`.
export async function post(path, body, label) {
    const options = { method: "POST" };
    if (body !== undefined) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(body);
    }

    let response;
    try {
        response = await fetch(path, options);
    } catch (error) {
        console.error("Request failed:", error);
        warnUser(`${label}: couldn't reach the server.`, "err");
        return { ok: false, status: 0, data: {} };
    }

    let data = {};
    try {
        data = await response.json();
    } catch (_) {
        // Non-JSON body; keep the empty object.
    }

    if (!response.ok) {
        const busy = response.status === 409 || response.status === 408;
        const reason = data.message || `request failed (HTTP ${response.status})`;
        warnUser(`${label}: ${reason}`, busy ? "warn" : "err");
    }
    return { ok: response.ok, status: response.status, data };
}
