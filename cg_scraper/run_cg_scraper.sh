#!/bin/sh
#
# run_cg_scraper.sh - Wrapper del scraper de RAM en compragamer.com.
#
# Mismo patrón que run_ml_scraper.sh: chequeo de conectividad, corrida del
# scraper (guarda en SQLite), gráfico histórico y mail. CompraGamer expone
# API propia, así que no necesita Playwright - más liviano y rápido.
#
# Códigos de salida: 0 = OK, 1 = falló (systemd reintenta).

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_CONF_PATH="${ENV_CONF_PATH:-$SCRIPT_DIR/../env.conf}"

if [ -f "$ENV_CONF_PATH" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_CONF_PATH"
    set +a
fi

: "${WIFI_INTERFACE:?falta WIFI_INTERFACE en env.conf}"
: "${PING_TARGET:?falta PING_TARGET en env.conf}"
: "${MAIN_DIR:?falta MAIN_DIR en env.conf}"
: "${LOG_DIR:?falta LOG_DIR en env.conf}"
: "${EMAIL_TO:?falta EMAIL_TO en env.conf}"
: "${MSMTP_ACCOUNT:?falta MSMTP_ACCOUNT en env.conf}"

PING_MAX_ATTEMPTS="${PING_MAX_ATTEMPTS:-10}"
PING_RESTART_DOWN_SECONDS="${PING_RESTART_DOWN_SECONDS:-5}"
PING_RESTART_UP_SECONDS="${PING_RESTART_UP_SECONDS:-15}"

export PYTHONPATH="$MAIN_DIR${PYTHONPATH:+:$PYTHONPATH}"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

send_error_mail() {
    subject="$1"
    body="$2"
    {
        echo "To: $EMAIL_TO"
        echo "Subject: $subject"
        echo "Content-Type: text/plain; charset=UTF-8"
        echo ""
        echo "$body"
    } | msmtp -a "$MSMTP_ACCOUNT" "$EMAIL_TO"
}

restart_wifi() {
    log "Reiniciando interfaz $WIFI_INTERFACE..."
    sudo ip link set "$WIFI_INTERFACE" down
    sleep "$PING_RESTART_DOWN_SECONDS"
    sudo ip link set "$WIFI_INTERFACE" up
    sleep "$PING_RESTART_UP_SECONDS"
}

check_connectivity() {
    attempt=0
    while [ "$attempt" -lt "$PING_MAX_ATTEMPTS" ]; do
        if ping -c 1 -W 3 "$PING_TARGET" >/dev/null 2>&1; then
            return 0
        fi
        restart_wifi
        attempt=$((attempt + 1))
    done
    return 1
}

# --- 1. Conectividad ---
log "Verificando conectividad..."
if ! check_connectivity; then
    log "Sin conectividad tras $PING_MAX_ATTEMPTS intentos."
    exit 1
fi
log "Conectividad OK."

# --- 2. Scraper ---
log "Corriendo scraper de RAM..."
if ! "$MAIN_DIR/.venv/bin/python3" "$MAIN_DIR/cg_scraper/cg_scraper.py" >"$LOG_DIR/cg_scraper_run.log" 2>&1; then
    log "El scraper falló. Ver $LOG_DIR/cg_scraper_run.log"
    send_error_mail \
        "RAM prices - ERROR ($(date +'%Y-%m-%d'))" \
        "El scraper de RAM falló. Log en el servidor: $LOG_DIR/cg_scraper_run.log"
    exit 1
fi
log "Scraper OK."

# --- 3. Mail ---
log "Armando y enviando reporte..."
TEMP_HTML=$(mktemp)
"$MAIN_DIR/.venv/bin/python3" "$MAIN_DIR/cg_scraper/cg_mail_report.py" "$TEMP_HTML"

{
    echo "To: $EMAIL_TO"
    echo "Subject: RAM prices report - $(date +'%Y-%m-%d')"
    echo "Content-Type: text/html; charset=UTF-8"
    echo "MIME-Version: 1.0"
    echo ""
    cat "$TEMP_HTML"
} | msmtp -a "$MSMTP_ACCOUNT" "$EMAIL_TO"

rm -f "$TEMP_HTML"
log "Reporte enviado correctamente."
exit 0
