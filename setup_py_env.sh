
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

create_python_env() {
    python3 -m venv $SCRIPT_DIR/.venv
    source $SCRIPT_DIR/.venv/bin/activate
    pip install -r $SCRIPT_DIR/requirements.txt
    $SCRIPT_DIR/.venv/bin/playwright install firefox
}

echo "== Creando entorno virtual e instalando dependencias =="
if [ -d "$SCRIPT_DIR/.venv" ]; then
  echo "Entorno presente"
else
  create_python_env
fi
echo "Listo."
