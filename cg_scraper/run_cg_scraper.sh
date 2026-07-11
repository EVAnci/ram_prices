#!/bin/sh

restart_rtl() {
  sudo ip link set wlp2s0 down 
  sleep 5
  sudo ip link set wlp2s0 up
  sleep 15
}

attempt=0
max_attempts=10

while [ $attempt -lt $max_attempts ]; do
  if ping -c 1 192.168.68.1; then
    break
  fi
  restart_rtl
  ((attempt++))
done

MAIN_PATH="/home/valen/ram_prices/"
LOG_DIR="/home/valen/Files/"
LOG_FILE="prices.log"
EMAIL="ancibrothers@gmail.com"

OUTPUT=$(python3 "$MAIN_PATH/market.py" 2>&1)
STATUS=$?

SUBJECT="RAM prices report - $(date +'%Y-%m-%d')"

if [ $STATUS -eq 0 ]; then
    # Guardar el output JSON en un archivo temporal
    TEMP_JSON=$(mktemp)
    echo "$OUTPUT" > "$TEMP_JSON"
    
    # Convertir JSON a HTML
    python3 "$MAIN_PATH/json2html.py" "$TEMP_JSON" "$LOG_DIR/table.html"
    
    # Crear el email con headers MIME correctos para HTML
    {
        echo "To: $EMAIL"
        echo "Subject: $SUBJECT"
        echo "Content-Type: text/html; charset=UTF-8"
        echo "MIME-Version: 1.0"
        echo ""
        cat "$LOG_DIR/table.html"
    } | msmtp -a gmail "$EMAIL"
    
    # Limpiar archivo temporal
    rm -f "$TEMP_JSON"
    
    echo "[+] Notification sent successfully."
else
    BODY="[-] The script ended with error, status: $STATUS."
    {
        echo "To: $EMAIL"
        echo "Subject: $SUBJECT"
        echo "Content-Type: text/plain; charset=UTF-8"
        echo ""
        echo "$BODY"
    } | msmtp -a gmail "$EMAIL"
    
    echo "[-] Error notification sent."
fi
