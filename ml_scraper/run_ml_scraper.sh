#!/bin/sh
#
# run_ml_scraper.sh - Wrapper del scraper de notebooks de MercadoLibre.
#
# 1. Verifica conectividad (reintentando bajar/subir la placa wifi si hace falta).
# 2. Corre el scraper (Playwright) -> guarda en SQLite.
# 3. Genera el gráfico histórico (boxplot).
# 4. Arma el HTML del reporte y lo manda por mail.
#
# Códigos de salida:
#   0 = todo OK (systemd no reintenta)
#   1 = falló algo (systemd reintenta según Restart=on-failure del .service)
#
# Config: ver env.conf (mismo directorio que este script, o el que indique
# la variable de entorno ENV_CONF_PATH).

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_CONF_PATH="${ENV_CONF_PATH:-$SCRIPT_DIR/../env.conf}"

# Si systemd ya nos dio las variables (via EnvironmentFile=), esto no pisa
# nada; si corremos a mano, las carga.
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

# db.py y config.py viven en la raíz del proyecto (se comparten con
# cg_scraper), no dentro de ml_scraper/. Los agregamos al PYTHONPATH para
# que "import db" / "import config" resuelvan sin duplicar archivos.
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
    # No mandamos mail acá: sin red, probablemente tampoco salga el mail.
    # Dejamos que systemd reintente más tarde.
    exit 1
fi
log "Conectividad OK."

# --- 2. Scraper ---
log "Corriendo scraper de notebooks..."
if ! "$MAIN_DIR/.venv/bin/python3" "$MAIN_DIR/ml_scraper/ml_scraper.py" >"$LOG_DIR/ml_scraper_run.log" 2>&1; then
    log "El scraper falló. Ver $LOG_DIR/ml_scraper_run.log"
    send_error_mail \
        "Notebook prices - ERROR ($(date +'%Y-%m-%d'))" \
        "El scraper de notebooks falló. Log adjunto en el servidor: $LOG_DIR/ml_scraper_run.log"
    exit 1
fi
log "Scraper OK."

# --- 3. Gráfico histórico ---
# log "Generando gráfico histórico..."
# "$MAIN_DIR/.venv/bin/python3" "$MAIN_DIR/ml_scraper/generate_report.py" >>"$LOG_DIR/ml_scraper_run.log" 2>&1 || \
#     log "[WARN] Falló la generación del gráfico, se manda el mail igual sin él."

# --- 4. Reporte por mail ---
log "Armando y enviando reporte..."
TEMP_HTML=$(mktemp)
"$MAIN_DIR/.venv/bin/python3" "$MAIN_DIR/ml_scraper/ml_mail_report.py" "$TEMP_HTML"

{
    echo "To: $EMAIL_TO"
    echo "Subject: Notebook prices report - $(date +'%Y-%m-%d')"
    echo "Content-Type: text/html; charset=UTF-8"
    echo "MIME-Version: 1.0"
    echo ""
    cat "$TEMP_HTML"
} | msmtp -a "$MSMTP_ACCOUNT" "$EMAIL_TO"

rm -f "$TEMP_HTML"
log "Reporte enviado correctamente."
exit 0
