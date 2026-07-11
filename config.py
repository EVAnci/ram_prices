# Minimal loader for env.conf intended for Python scripts.

# If the process is launched by systemd using "EnvironmentFile=env.conf",
# the variables are already present in os.environ and this module does 
# nothing (it does not overwrite existing values). If the script is 
# run manually from a terminal, this loader parses env.conf and 
# populates os.environ.

# Usage:
#     from config import get_config
#     cfg = get_config()
#     print(cfg["ML_DB_PATH"])

# Or directly:
#     import config
#     config.load()  # populates os.environ
#     os.environ["ML_DB_PATH"]

import os
from pathlib import Path

DEFAULT_ENV_PATH = Path(__file__).parent / "env.conf"

_LINE_RE_COMMENT = "#"


def load(env_path: Path | str = DEFAULT_ENV_PATH) -> None:
    """Parses env.conf and completes os.environ (without overwrite)."""
    env_path = Path(env_path)
    if not env_path.exists():
        raise FileNotFoundError(f"[config.py] - Config file not found: {env_path}")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(_LINE_RE_COMMENT) or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        # Don't overwrite if systemd already set the value.
        os.environ.setdefault(key, value)


def get_config(env_path: Path | str = DEFAULT_ENV_PATH) -> dict:
    load(env_path)
    keys = [
        "RAM_DIR", "ML_DIR", "LOG_DIR",
        "ML_DB_PATH", "ML_REPORT_IMG",
        "RAM_LOG_FILE", "RAM_RAW_LOG_FILE",
        "EMAIL_TO", "MSMTP_ACCOUNT",
        "WIFI_INTERFACE", "PING_TARGET", "PING_MAX_ATTEMPTS",
        "PING_RESTART_DOWN_SECONDS", "PING_RESTART_UP_SECONDS",
    ]
    return {k: os.environ.get(k) for k in keys}


if __name__ == "__main__":
    import json
    print(json.dumps(get_config(), indent=2, ensure_ascii=False))
