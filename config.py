"""
Loader mínimo de env.conf para los scripts en Python.

Si el proceso ya fue lanzado por systemd con "EnvironmentFile=env.conf",
las variables ya están en os.environ y este módulo no hace nada extra
(no pisa lo que ya esté seteado). Si corrés el script a mano desde la
terminal, este loader parsea env.conf y completa os.environ.

Uso:
    from config import get_config
    cfg = get_config()
    print(cfg["ML_DB_PATH"])

O directamente:
    import config
    config.load()  # completa os.environ
    os.environ["ML_DB_PATH"]
"""

import os
from pathlib import Path

DEFAULT_ENV_PATH = Path(__file__).parent / "env.conf"

_LINE_RE_COMMENT = "#"


def load(env_path: Path | str = DEFAULT_ENV_PATH) -> None:
    """Parsea env.conf y completa os.environ (sin pisar variables ya seteadas)."""
    env_path = Path(env_path)
    if not env_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de config: {env_path}")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(_LINE_RE_COMMENT) or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        # No pisamos si systemd (u otro entorno) ya nos dio un valor.
        os.environ.setdefault(key, value)


def get_config(env_path: Path | str = DEFAULT_ENV_PATH) -> dict:
    load(env_path)
    keys = [
        "MAIN_DIR", "DB_DIR", "FILES_DIR", "LOG_DIR",
        "SCRAPER_DB_PATH", "ML_REPORT_IMG", "RAM_REPORT_IMG",
        "EMAIL_TO", "MSMTP_ACCOUNT",
        "WIFI_INTERFACE", "PING_TARGET", "PING_MAX_ATTEMPTS",
        "PING_RESTART_DOWN_SECONDS", "PING_RESTART_UP_SECONDS",
    ]
    return {k: os.environ.get(k) for k in keys}


if __name__ == "__main__":
    import json
    print(json.dumps(get_config(), indent=2, ensure_ascii=False))
