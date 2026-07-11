#!/bin/sh
#
# run_ml_scraper.sh - Wrapper for the ML notebook scraper.
#
# 1. Verifies connectivity (retries bringing the Wi-Fi interface down/up if necessary).
# 2. Runs the scraper (Playwright) -> saves to SQLite.
# 3. Generates the historical chart (boxplot).
# 4. Assembles the HTML report and sends it via email.
#
# Exit codes:
#    0 = success (systemd will not retry)
#    1 = failure (systemd will retry based on Restart=on-failure in the .service file)
#
# Config: see env.conf (located in the same directory as this script, or 
# defined by the ENV_CONF_PATH environment variable).

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_CONF_PATH="${ENV_CONF_PATH:-$SCRIPT_DIR/env.conf}"

# If the script is executed with systemd variables won't be overwriten
if [ -f "$ENV_CONF_PATH" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ENV_CONF_PATH"
    set +a
fi

: "${WIFI_INTERFACE:?missing WIFI_INTERFACE in env.conf}"
: "${PING_TARGET:?missing PING_TARGET in env.conf}"
: "${ML_DIR:?missing ML_DIR in env.conf}"
: "${LOG_DIR:?missing LOG_DIR in env.conf}"
: "${EMAIL_TO:?missing EMAIL_TO in env.conf}"
: "${MSMTP_ACCOUNT:?missing MSMTP_ACCOUNT in env.conf}"

PING_MAX_ATTEMPTS="${PING_MAX_ATTEMPTS:-10}"
PING_RESTART_DOWN_SECONDS="${PING_RESTART_DOWN_SECONDS:-5}"
PING_RESTART_UP_SECONDS="${PING_RESTART_UP_SECONDS:-15}"

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
    log "[run_ml_scrapper.sh] -> Restarting interface $WIFI_INTERFACE..."
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

# --- 1. Check conectivity ---
log "[run_ml_scraper.sh] -> Checking connectivity conectividad..."
if ! check_connectivity; then
    log "[run_ml_scraper.sh] -> Network unavailable after $PING_MAX_ATTEMPTS tries."
    exit 1
fi
log "[run_ml_scraper.sh] -> Network status: Available."

# --- 2. Scraper ---
log "[run_ml_scraper.sh] -> Running notebook scraper..."
if ! python3 "$ML_DIR/ml_scrapper.py" >"$LOG_DIR/ml_scraper_last_run.log" 2>&1; then
    log "[run_ml_scraper.sh] -> Scraper script ended with error. See $LOG_DIR/ml_scraper_last_run.log"
    send_error_mail \
        "Notebook prices - ERROR ($(date +'%Y-%m-%d'))" \
        "El scraper de notebooks falló. Log adjunto en el servidor: $LOG_DIR/ml_scraper_last_run.log"
    exit 1
fi
log "[run_ml_scraper.sh] -> Scraper OK."

# --- 3. Time Plot ---
log "[run_ml_scraper.sh] -> Generating plot..."
python3 "$ML_DIR/generate_report.py" >>"$LOG_DIR/ml_scraper_last_run.log" 2>&1 || \
    log "[run_ml_scraper.sh] -> [WARN] Plot generation failed | Sending mail without plot."

# --- 4. Mail report ---
log "[run_ml_scraper.sh] -> Sending report..."
TEMP_HTML=$(mktemp)
python3 "$ML_DIR/ml_mail_report.py" "$TEMP_HTML"

{
    echo "To: $EMAIL_TO"
    echo "Subject: Notebook prices report - $(date +'%Y-%m-%d')"
    echo "Content-Type: text/html; charset=UTF-8"
    echo "MIME-Version: 1.0"
    echo ""
    cat "$TEMP_HTML"
} | msmtp -a "$MSMTP_ACCOUNT" "$EMAIL_TO"

rm -f "$TEMP_HTML"
log "[run_ml_scraper.sh] -> Sended successfully."
exit 0
