# AGENTS.md

## Hardware & Runtime Constraints (Critical)
- **Target Hardware:** Intel Atom N2600 processor (supports up to SSSE3, lacks SSE4.2).

## Environment & Setup
- **Virtual Environment:** `.venv` in project root.
- **Setup Script:** `./setup_py_env.sh` (creates venv, installs dependencies from `requirements.txt`, installs Playwright firefox).
- **Configuration:** Copy `env.conf.example` to `env.conf`.

## Architecture & Entrypoints
- **Python Path:** `PYTHONPATH` must include the project root (`$MAIN_DIR`) so shared modules (`db`, etc.) resolve correctly.
- **CompraGamer Scraper:** `cg_scraper/cg_scraper.py` (uses `requests` for the CG API). Wrapper: `cg_scraper/run_cg_scraper.sh`.
- **MercadoLibre Scraper:** `ml_scraper/ml_scraper.py` (uses Playwright with Firefox). Wrapper: `ml_scraper/run_ml_scraper.sh`.
- **Database:** SQLite DB managed via `db/db.py` following schema `db/schema.sql`.

## Systemd Automation
- **Units:** Located in `systemd_units/` (`cg_scraper.service/.timer`, `ml_scraper.service/.timer`).
- **Deployment:** Run `sudo ./conf_env.sh` to install units, enable timers, and automatically generate the NOPASSWD sudoers file defined by `SUDO_NET` in `env.conf`.
- **Resilience:** Wrappers use `sudo -n` for non-interactive `ip link` / `nmcli` network resets. Services include `TimeoutStartSec=10min` and `Restart=on-failure` to prevent infinite hangs in `activating` state.
