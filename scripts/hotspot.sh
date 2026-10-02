#!/usr/bin/env bash
# Switch the Pi between its own Wi-Fi network (for observing outside, no
# internet needed) and your normal home Wi-Fi.
#
#   bash scripts/hotspot.sh on       start the Pi's own network (stays on after reboots)
#   bash scripts/hotspot.sh off      back to home Wi-Fi
#   bash scripts/hotspot.sh status   show which network the Pi is on
#
# The first "on" asks for a network name and password. NetworkManager stores
# them in /etc/NetworkManager (root only), never in this repo.
#
# Switching networks drops the SSH session you ran this from, so the switch
# itself runs as a background systemd job that the drop can't interrupt. It has
# a safety net: if the new network doesn't come up within SWITCH_TIMEOUT
# seconds, the Pi goes back to the one it came from, so it never ends up
# unreachable. Progress is logged to $LOG.

set -euo pipefail

CON="telescope-hotspot"     # NetworkManager connection name
IFACE="wlan0"
PI_ADDR="10.42.0.1"         # NetworkManager's address for the Pi in "shared" mode
APP_PORT="${PORT:-5000}"
SWITCH_TIMEOUT=30
LOG="/tmp/telescope-hotspot.log"
SCRIPT="$(readlink -f "$0")"

hotspot_exists() {
    nmcli -t -f NAME connection show | grep -qx "$CON"
}

hotspot_ssid() {
    nmcli -g 802-11-wireless.ssid connection show "$CON"
}

active_connection() {
    nmcli -t -f GENERAL.CONNECTION device show "$IFACE" | cut -d: -f2
}

create_hotspot() {
    local ssid pass
    read -rp "Network name [Telescope]: " ssid
    ssid="${ssid:-Telescope}"
    while true; do
        read -rsp "Password (at least 8 characters): " pass
        echo
        [ "${#pass}" -ge 8 ] && break
        echo "Too short, try again."
    done
    # 2.4 GHz (band bg) reaches further outdoors; WPA2 works with any laptop or phone
    sudo nmcli connection add type wifi ifname "$IFACE" con-name "$CON" ssid "$ssid" \
        802-11-wireless.mode ap 802-11-wireless.band bg \
        ipv4.method shared ipv6.method disabled \
        wifi-sec.key-mgmt wpa-psk wifi-sec.proto rsn \
        wifi-sec.pairwise ccmp wifi-sec.group ccmp \
        wifi-sec.psk "$pass" >/dev/null
    connection_autoconnect no     # only "on" enables it, after the switch succeeds
    echo "Created hotspot \"$ssid\"."
}

connection_autoconnect() {
    sudo nmcli connection modify "$CON" connection.autoconnect "$1" connection.autoconnect-priority 100
}

# Run "$SCRIPT _apply <on|off>" as root in its own systemd job, detached from this SSH session
run_detached() {
    sudo systemd-run --quiet --collect --unit="telescope-hotspot-$(date +%s)" \
        /usr/bin/env bash "$SCRIPT" _apply "$1"
}

log() {
    echo "$(date '+%F %T') $*" >> "$LOG"
}

# ---------- The detached part (runs as root, survives the SSH drop) ----------

apply_on() {
    log "Switching to the hotspot..."
    if nmcli --wait "$SWITCH_TIMEOUT" connection up "$CON" >> "$LOG" 2>&1; then
        nmcli connection modify "$CON" connection.autoconnect yes connection.autoconnect-priority 100
        log "Hotspot is on (stays on after reboots until you run 'off')."
    else
        log "Hotspot failed to start; going back to home Wi-Fi."
        nmcli connection modify "$CON" connection.autoconnect no
        nmcli --wait "$SWITCH_TIMEOUT" device connect "$IFACE" >> "$LOG" 2>&1 || log "No known Wi-Fi in range either."
    fi
}

apply_off() {
    log "Switching back to home Wi-Fi..."
    nmcli connection modify "$CON" connection.autoconnect no
    nmcli connection down "$CON" >> "$LOG" 2>&1 || true
    if nmcli --wait "$SWITCH_TIMEOUT" device connect "$IFACE" >> "$LOG" 2>&1 \
            && [ "$(active_connection)" != "$CON" ] && [ -n "$(active_connection)" ]; then
        log "Connected to \"$(active_connection)\"."
    else
        # Safety net: no known Wi-Fi in range, so bring the hotspot back rather than
        # leave the Pi with no network at all
        log "No known Wi-Fi in range; turning the hotspot back on so the Pi stays reachable."
        nmcli connection modify "$CON" connection.autoconnect yes connection.autoconnect-priority 100
        nmcli --wait "$SWITCH_TIMEOUT" connection up "$CON" >> "$LOG" 2>&1 || log "Hotspot failed to start too."
    fi
}

# ---------- Commands ----------

case "${1:-status}" in
    on)
        hotspot_exists || create_hotspot
        sudo -v     # ask for the password now, while you can still answer
        echo "Switching to the hotspot. If you're connected over home Wi-Fi, this SSH session will drop."
        echo "Then join \"$(hotspot_ssid)\" and use ssh $(whoami)@$PI_ADDR / http://$PI_ADDR:$APP_PORT"
        echo "If the hotspot doesn't appear within ${SWITCH_TIMEOUT}s, the Pi goes back to home Wi-Fi."
        run_detached on
        ;;
    off)
        if ! hotspot_exists; then
            echo "No hotspot has been set up yet."
            exit 0
        fi
        sudo -v
        echo "Switching back to home Wi-Fi. If you're connected over the hotspot, this SSH session will drop."
        echo "Then reconnect your laptop to home Wi-Fi and use ssh $(whoami)@$(hostname).local"
        echo "If no known Wi-Fi is in range within ${SWITCH_TIMEOUT}s, the hotspot comes back on."
        run_detached off
        ;;
    status)
        active="$(active_connection)"
        if [ "$active" = "$CON" ]; then
            echo "Hotspot is ON. Join \"$(hotspot_ssid)\" and open http://$PI_ADDR:$APP_PORT"
        elif [ -n "$active" ]; then
            echo "Hotspot is off. $IFACE is on \"$active\"."
        else
            echo "Hotspot is off and $IFACE isn't connected to anything."
        fi
        if [ -f "$LOG" ]; then
            echo "Last switch:"
            tail -n 3 "$LOG" | sed 's/^/  /'
        fi
        ;;
    _apply)
        # Internal: called by run_detached as root
        case "${2:-}" in
            on) apply_on ;;
            off) apply_off ;;
            *) exit 1 ;;
        esac
        ;;
    *)
        echo "Usage: bash scripts/hotspot.sh on|off|status" >&2
        exit 1
        ;;
esac
