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

set -euo pipefail

CON="telescope-hotspot"     # NetworkManager connection name
IFACE="wlan0"
PI_ADDR="10.42.0.1"         # NetworkManager's address for the Pi in "shared" mode
APP_PORT="${PORT:-5000}"

hotspot_exists() {
    nmcli -t -f NAME connection show | grep -qx "$CON"
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
    echo "Created hotspot \"$ssid\"."
}

case "${1:-status}" in
    on)
        hotspot_exists || create_hotspot
        # Autoconnect with high priority so it comes back after a reboot or power cycle
        sudo nmcli connection modify "$CON" connection.autoconnect yes connection.autoconnect-priority 100
        echo "Starting the hotspot. If you're connected over home Wi-Fi, this SSH session will drop."
        echo "Then join \"$(nmcli -g 802-11-wireless.ssid connection show "$CON")\" and open http://$PI_ADDR:$APP_PORT"
        sudo nmcli connection up "$CON" >/dev/null
        echo "Hotspot is on."
        ;;
    off)
        if hotspot_exists; then
            sudo nmcli connection modify "$CON" connection.autoconnect no
            sudo nmcli connection down "$CON" >/dev/null 2>&1 || true
        fi
        echo "Hotspot is off. Reconnecting to a known Wi-Fi network..."
        sudo nmcli device connect "$IFACE" >/dev/null 2>&1 \
            && echo "Connected: $(nmcli -t -f GENERAL.CONNECTION device show "$IFACE" | cut -d: -f2)" \
            || echo "No known Wi-Fi in range. Run 'bash scripts/hotspot.sh on' to get back in."
        ;;
    status)
        active="$(nmcli -t -f GENERAL.CONNECTION device show "$IFACE" | cut -d: -f2)"
        if [ "$active" = "$CON" ]; then
            echo "Hotspot is ON. Join \"$(nmcli -g 802-11-wireless.ssid connection show "$CON")\" and open http://$PI_ADDR:$APP_PORT"
        elif [ -n "$active" ]; then
            echo "Hotspot is off. $IFACE is on \"$active\"."
        else
            echo "Hotspot is off and $IFACE isn't connected to anything."
        fi
        ;;
    *)
        echo "Usage: bash scripts/hotspot.sh on|off|status" >&2
        exit 1
        ;;
esac
