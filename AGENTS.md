# AGENTS.md

## Hardware & Runtime
- **CPU:** Intel Atom N2600 (SSSE3 only). Avoid libraries requiring SSE4.2+.
- **Setup:** Run `./setup_py_env.sh` (installs deps + Playwright).
- **Config:** Copy `env.conf.example` to `env.conf`.

## Scrapers & Data
- **Run from Root:** Imports require root execution.
- **CompraGamer:** `cg_scraper/run_cg_scraper.sh` (requests).
- **MercadoLibre:** `ml_scraper/run_ml_scraper.sh` (Playwright).
- **Database:** SQLite at `db/scraper.db` (Schema: `db/schema.sql`).

## Frontend
- **Entry:** `frontend/main.py` (FastAPI).
- **Product ID Logic:** `ram_ddr<X>_<cap>gb` or `laptop_<marca>_<linea>`.
- **Query Case:** `cpu_line.marca` is `UPPERCASE` in DB. When querying by brand (e.g., `product_id`), normalize: `Intel`/`AMD` (e.g., `parts[0].capitalize()` for intel, `.upper()` for AMD).

## Systemd (Deploy)
- **Files:** `systemd_units/`.
- **Deploy:** `sudo ./conf_env.sh` (installs units, timers, sudoers).
- **Service Resilience:** `Restart=on-failure`, `TimeoutStartSec=10min`. Wrappers use `sudo -n` for network resets.
