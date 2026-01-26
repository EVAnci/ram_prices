#!/bin/bash

# Ruta absoluta a tus archivos
SCRIPT_PATH="/ruta/a/tu/market.py"
LOG_FILE="/ruta/a/tu/prices.log"
EMAIL="tu_destino@gmail.com"

# Ejecutar el script y capturar la salida (stdout y stderr)
OUTPUT=$(python3 "$SCRIPT_PATH" 2>&1)
STATUS=$?

if [ $STATUS -eq 0 ]; then
    # Preparar el cuerpo del mensaje
    SUBJECT="Reporte de Precios RAM - $(date +'%Y-%m-%d')"
    BODY="La tarea se ejecutó correctamente.\n\nSalida del script:\n\n$OUTPUT"
    
    # Enviar correo
    echo -e "Subject: $SUBJECT\n\n$BODY" | msmtp -a gmail "$EMAIL"
    echo "[+] Notificación enviada correctamente."
else
    echo "[-] El script falló con estado $STATUS. No se envió correo."
fi
