#!/bin/sh

MAIN_PATH="/full/path/to/ram_prices/"
LOG_DIR="/path/to/log/directory/"
LOG_FILE="prices.log"
EMAIL="mail@example"

OUTPUT=$(python3 "$MAIN_PATH/market.py" 2>&1)
STATUS=$?

SUBJECT="RAM prices report - $(date +'%Y-%m-%d')"
if [ $STATUS -eq 0 ]; then
    python "$MAIN_PATH/json2htmlTable.py" "$OUTPUT" "$LOG_DIR/table.html"
    BODY="$(cat $LOG_DIR/table.html)"

    echo -e "Subject: $SUBJECT\n\n$BODY" | msmtp -a gmail "$EMAIL"
    echo "[+] Notification sent successfuly."
else
    BODY="[-] The script ended with error, status: $STATUS."
    echo -e "Subject: $SUBJECT\n\n$BODY" | msmtp -a gmail "$EMAIL"
fi
