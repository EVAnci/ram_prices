# Persistencia en SQLite para el histórico de precios de notebooks scrapeados.

# Esquema:
#     scrape_runs(id, timestamp)       -- una fila por corrida del scraper
#     listings(id, run_id, item_id,    -- una fila por producto encontrado
#              title, price, currency, url)

# Uso típico dentro de ml_scrapper.py:

#     from db import init_db, save_run

#     products = scrape_all()
#     init_db()
#     save_run(products)

import os
import re
import sqlite3
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path

import config

config.load()  # completa os.environ desde env.conf si no fue seteado por systemd

DB_PATH = Path(os.environ.get("ML_DB_PATH", Path(__file__).parent / "precios_notebooks.db"))

ITEM_ID_RE = re.compile(r"(MLA-?\d+)", re.IGNORECASE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES scrape_runs(id),
    item_id TEXT,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    currency TEXT NOT NULL,
    url TEXT
);

CREATE INDEX IF NOT EXISTS idx_listings_run_id ON listings(run_id);
CREATE INDEX IF NOT EXISTS idx_listings_item_id ON listings(item_id);
"""


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def extract_item_id(url: str | None) -> str | None:
    if not url:
        return None
    match = ITEM_ID_RE.search(url)
    return match.group(1).upper().replace("MLA-", "MLA") if match else None


def save_run(products: list, timestamp: datetime | None = None) -> int:
    """Guarda una corrida completa. Devuelve el run_id insertado."""
    ts = (timestamp or datetime.now(timezone.utc)).isoformat()

    with get_connection() as conn:
        cur = conn.execute("INSERT INTO scrape_runs (timestamp) VALUES (?)", (ts,))
        run_id = cur.lastrowid

        rows = [
            (
                run_id,
                extract_item_id(p.url if hasattr(p, "url") else p.get("url")),
                p.title if hasattr(p, "title") else p["title"],
                p.price if hasattr(p, "price") else p["price"],
                p.currency if hasattr(p, "currency") else p["currency"],
                p.url if hasattr(p, "url") else p.get("url"),
            )
            for p in products
        ]
        conn.executemany(
            "INSERT INTO listings (run_id, item_id, title, price, currency, url) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()

    print(f"[DB] Corrida guardada (run_id={run_id}, {len(rows)} productos) en {DB_PATH}")
    return run_id


def load_history_df():
    """Devuelve un DataFrame de pandas con todo el histórico (una fila por producto)."""
    import pandas as pd

    with get_connection() as conn:
        df = pd.read_sql(
            """
            SELECT
                r.timestamp,
                l.item_id,
                l.title,
                l.price,
                l.currency,
                l.url
            FROM listings l
            JOIN scrape_runs r ON l.run_id = r.id
            ORDER BY r.timestamp
            """,
            conn,
            parse_dates=["timestamp"],
        )
    return df
