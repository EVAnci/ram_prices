#!/bin/sh
#
# conf_env.sh - Instala/actualiza las unidades systemd de los scrapers
# de precios (RAM + notebooks) y las habilita. Idempotente: se puede
# correr de nuevo cada vez que cambian los .service/.timer.
#
# Uso:
#   sudo ./conf_env.sh
#
# Requiere correr como root (o con sudo) porque instala en /etc/systemd/system.

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Este script necesita privilegios de root. Corré: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UNITS_SRC_DIR="$SCRIPT_DIR/systemd_units"
SYSTEMD_DIR="/etc/systemd/system"

ENV_CONF_PATH="${ENV_CONF_PATH:-$SCRIPT_DIR/env.conf}"
if [ -f "$ENV_CONF_PATH" ]; then
    set -a
    . "$ENV_CONF_PATH"
    set +a
fi

if [ -n "${SUDO_NET:-}" ]; then
    echo "== Configurando reglas sudoers en $SUDO_NET =="
    SCRAPER_USER=""
    if [ -f "$UNITS_SRC_DIR/cg_scraper.service" ]; then
        SCRAPER_USER="$(grep -E '^User=' "$UNITS_SRC_DIR/cg_scraper.service" | cut -d= -f2 | tr -d '[:space:]')"
    fi
    if [ -z "$SCRAPER_USER" ] && [ -n "${SUDO_USER:-}" ]; then
        SCRAPER_USER="$SUDO_USER"
    fi
    SCRAPER_USER="${SCRAPER_USER:-valen}"

    WIFI_IF="${WIFI_INTERFACE:-wlp2s0}"
    IP_PATH="$(command -v ip || echo /usr/bin/ip)"
    NMCLI_PATH="$(command -v nmcli || echo /usr/bin/nmcli)"

    sudoers_content="$SCRAPER_USER ALL=(ALL) NOPASSWD: $IP_PATH link set $WIFI_IF down, $IP_PATH link set $WIFI_IF up"
    if [ -x "$NMCLI_PATH" ]; then
        sudoers_content="$sudoers_content, $NMCLI_PATH device connect $WIFI_IF, $NMCLI_PATH device disconnect $WIFI_IF"
    fi

    echo "$sudoers_content" > "$SUDO_NET"
    chmod 440 "$SUDO_NET"

    if command -v visudo >/dev/null 2>&1; then
        if visudo -cf "$SUDO_NET"; then
            echo "[ok] Regla sudoers validada correctamente en $SUDO_NET"
        else
            echo "[error] Error de sintaxis en el archivo sudoers generado." >&2
            exit 1
        fi
    else
        echo "[ok] Archivo sudoers creado en $SUDO_NET"
    fi
fi

UNITS="ml_scraper.service ml_scraper.timer cg_scraper.service cg_scraper.timer"

install_unit() {
    unit_file="$1"
    src="$UNITS_SRC_DIR/$unit_file"

    if [ ! -f "$src" ]; then
        echo "[skip] $unit_file no está en $UNITS_SRC_DIR, lo salteo."
        return
    fi

    dst="$SYSTEMD_DIR/$unit_file"
    if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
        echo "[ok]   $unit_file ya está instalado y sin cambios."
        return
    fi

    cp "$src" "$dst"
    chmod 644 "$dst"
    echo "[copy] $unit_file -> $dst"
}

echo "== Instalando unidades systemd =="
for unit in $UNITS; do
    install_unit "$unit"
done

echo "== Marcando los scripts como ejecutables =="
chmod +x "$SCRIPT_DIR/ml_scraper/run_ml_scraper.sh" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/cg_scraper/run_cg_scraper.sh" 2>/dev/null || true

echo "== Recargando systemd =="
systemctl daemon-reload

echo "== Habilitando timers =="
for unit in $UNITS; do
    case "$unit" in
        *.timer)
            if [ -f "$SYSTEMD_DIR/$unit" ]; then
                systemctl enable --now "$unit"
                echo "[enable] $unit"
            fi
            ;;
    esac
done

echo ""
echo "Listo. Estado actual:"
systemctl list-timers --all | grep -E "ml_scraper|cg_scraper" || true

echo ""
echo "Para ver el próximo disparo y logs:"
echo "  systemctl status ml_scraper.timer"
echo "  journalctl -u ml_scraper.service -f"
