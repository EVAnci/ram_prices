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

create_python_env() {
    python3 -m venv $SCRIPT_DIR/.venv
    source $SCRIPT_DIR/.venv/bin/activate
    pip install -r $SCRIPT_DIR/requirements.txt
    $SCRIPT_DIR/.venv/bin/playwright install firefox
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

echo "== Creando entorno virtual e instalando dependencias =="
create_python_env
echo "Listo."
