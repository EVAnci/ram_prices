#!/bin/sh
#
# conf_env.sh - Installs/updates and enables systemd units for the price 
# scrapers (RAM + notebooks). Idempotent: can be run again whenever the 
# .service/.timer files are modified.
#
# Usage:
#    sudo ./conf_env.sh
#
# Must be run as root (or with sudo) as it installs files to /etc/systemd/system.

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Este script necesita privilegios de root. Corré: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

UNITS="notebook-precio.service notebook-precio.timer"
# If RAM scripts are in the same directory, will also be installed.
# Comment this line if you wan't them to be elsewhere.
UNITS="$UNITS precio-ram.service precio-ram.timer"

install_unit() {
    unit_file="$1"
    src="$SCRIPT_DIR/$unit_file"

    if [ ! -f "$src" ]; then
        echo "[conf_env.sh] -> [skip] $unit_file not in $SCRIPT_DIR, skipping."
        return
    fi

    dst="$SYSTEMD_DIR/$unit_file"
    if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
        echo "[conf_env.sh] -> [ok]   $unit_file allready installed."
        return
    fi

    cp "$src" "$dst"
    chmod 644 "$dst"
    echo "[conf_env.sh] -> [copy] $unit_file -> $dst"
}

echo "[conf_env.sh] -> == Installing systemd units =="
for unit in $UNITS; do
    install_unit "$unit"
done

echo "[conf_env.sh] -> == Setting execution permisions to scripts =="
chmod +x "$SCRIPT_DIR/run_ml_scraper.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/cronwork.sh" 2>/dev/null || true

echo "[conf_env.sh] -> == Reloading systemd =="
systemctl daemon-reload

echo "[conf_env.sh] -> == Enabling timers =="
for unit in $UNITS; do
    case "$unit" in
        *.timer)
            if [ -f "$SYSTEMD_DIR/$unit" ]; then
                systemctl enable --now "$unit"
                echo "[conf_env.sh] -> [enable] $unit"
            fi
            ;;
    esac
done

echo ""
echo "[conf_env.sh] -> Done. Status:"
systemctl list-timers --all | grep -E "notebook-precio|precio-ram" || true

echo ""
echo "[conf_env.sh] -> To see next shoot and logs:"
echo "                  systemctl status notebook-precio.timer"
echo "                  journalctl -u notebook-precio.service -f"
