# AGENTS.md

## Project execution

- The real environment is in a LAN server. This project is the development spaces so db, scrapers and services are not running in this machine.

## Hardware & Runtime
- **CPU Constraint:** Intel Atom N2600 (SSSE3 only, no SSE4.2). Avoid libraries requiring modern CPU extensions.

## Environment & Setup
- **Venv:** `.venv` in project root.
- **Install:** `./setup_py_env.sh` (installs deps + Playwright firefox).
- **Config:** Copy `env.conf.example` to `env.conf`.

## Architecture & Entrypoints
- **Python Path:** Must run from project root to resolve imports (`PYTHONPATH` set internally or externally).
- **Scrapers:**
  - **CompraGamer:** `cg_scraper/run_cg_scraper.sh` (uses `requests`).
  - **MercadoLibre:** `ml_scraper/run_ml_scraper.sh` (uses Playwright).
- **Database:** SQLite (`db/scraper.db`), schema in `db/schema.sql`.

## Frontend
- **Server:** `frontend/main.py` (FastAPI).
- **Service:** `systemd_units/frontend.service` handles deployment.
- **Product ID Logic:** `ram_ddr<X>_<cap>gb` or `laptop_<marca>_<linea>`.
- **Case Sensitivity:** `cpu_line.marca` in DB is `UPPERCASE`. When querying by brand from `product_id`, ensure `Intel` / `AMD` format (e.g., `parts[0].capitalize() if parts[0] == 'intel' else parts[0].upper()`).

## Systemd
- **Units:** `systemd_units/` (*.service, *.timer).
- **Deploy:** `sudo ./conf_env.sh` (installs units, enables timers, generates NOPASSWD sudoers).
- **Resilience:** Wrappers use `sudo -n` for non-interactive network resets. Services have `Restart=on-failure` and `TimeoutStartSec=10min`.
