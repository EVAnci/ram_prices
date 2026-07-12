"""
Persistencia en SQLite con el esquema normalizado (ver schema.sql):

    providers -> scrape_runs -> listings -> laptops | ram
                                              ^
                                cpu_line -----+  (solo laptops)

API pensada para ser usada por ambos scrapers (ml_scraper y cg_scraper),
cada uno guardando en las tablas hijas que le correspondan.
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import config

config.load()  # completa os.environ desde env.conf si no fue seteado por systemd

DB_PATH = Path(
    os.environ.get("SCRAPER_DB_PATH")
    or (Path(os.environ.get("DB_DIR", Path(__file__).parent)) / "scraper.db")
)
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Crea las tablas si no existen y carga los datos semilla. Idempotente."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------
# Lookups
# ----------------------------------------------------------------------------

def get_provider_id(conn: sqlite3.Connection, nombre: str) -> int:
    row = conn.execute(
        "SELECT id FROM providers WHERE nombre = ?", (nombre,)
    ).fetchone()
    if row is None:
        raise ValueError(
            f"Proveedor '{nombre}' no existe en la tabla providers. "
            f"Agregalo en schema.sql o insertalo a mano."
        )
    return row[0]


def get_product_type_id(conn: sqlite3.Connection, slug: str) -> int:
    row = conn.execute(
        "SELECT id FROM product_types WHERE slug = ?", (slug,)
    ).fetchone()
    if row is None:
        raise ValueError(f"product_type '{slug}' no existe en product_types.")
    return row[0]


def get_cpu_line_id(conn: sqlite3.Connection, marca: str, linea: str) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM cpu_line WHERE marca = ? AND linea = ?", (marca, linea)
    ).fetchone()
    if row is None:
        print(
            f"[WARN] cpu_line ('{marca}', '{linea}') no está en el catálogo. "
            f"Se guarda el listing con cpu_line_id = NULL. "
            f"Agregala a mano en la tabla cpu_line si querés clasificarla."
        )
        return None
    return row[0]


# ----------------------------------------------------------------------------
# Corridas
# ----------------------------------------------------------------------------

def start_run(conn: sqlite3.Connection, provider_nombre: str, timestamp: Optional[datetime] = None) -> int:
    provider_id = get_provider_id(conn, provider_nombre)
    ts = (timestamp or datetime.now(timezone.utc)).isoformat()
    cur = conn.execute(
        "INSERT INTO scrape_runs (provider_id, ejecutado_en) VALUES (?, ?)",
        (provider_id, ts),
    )
    return cur.lastrowid


# ----------------------------------------------------------------------------
# Guardado - Notebooks
# ----------------------------------------------------------------------------

def save_laptop_listings(
    run_id: int,
    products: list,          # objetos con .title/.price/.currency/.url (o dicts)
    cpu_marca: str,
    cpu_linea: str,
    ram_gb: Optional[int] = None,
    storage_gb: Optional[int] = None,
    storage_tipo: Optional[str] = None,
) -> int:
    """
    Guarda una lista de productos de notebooks bajo una misma clasificación
    de CPU/RAM/storage (la clasificación es un parámetro de LA CORRIDA, no
    se infiere por título individual - ver charla de diseño).
    """
    with get_connection() as conn:
        product_type_id = get_product_type_id(conn, "laptop")
        cpu_line_id = get_cpu_line_id(conn, cpu_marca, cpu_linea)

        count = 0
        for p in products:
            title = p.title if hasattr(p, "title") else p["title"]
            price = p.price if hasattr(p, "price") else p["price"]
            currency = p.currency if hasattr(p, "currency") else p["currency"]
            url = p.url if hasattr(p, "url") else p.get("url")

            cur = conn.execute(
                "INSERT INTO listings (run_id, product_type_id, titulo, precio, moneda, url) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, product_type_id, title, price, currency, url),
            )
            listing_id = cur.lastrowid

            conn.execute(
                "INSERT INTO laptops (listing_id, cpu_line_id, ram_gb, storage_gb, storage_tipo) "
                "VALUES (?, ?, ?, ?, ?)",
                (listing_id, cpu_line_id, ram_gb, storage_gb, storage_tipo),
            )
            count += 1

        conn.commit()

    print(f"[DB] {count} notebooks guardadas (run_id={run_id}, cpu={cpu_marca} {cpu_linea}) en {DB_PATH}")
    return count


# ----------------------------------------------------------------------------
# Guardado - RAM
# ----------------------------------------------------------------------------

def save_ram_listings(run_id: int, items: list) -> int:
    """
    items: lista de dicts con al menos:
        titulo/nombre, precio, capacidad_gb, ddr, url (opcional)
    """
    with get_connection() as conn:
        product_type_id = get_product_type_id(conn, "ram")

        count = 0
        for item in items:
            title = item.get("nombre") or item.get("titulo") or ""
            price = item["precio"]
            currency = item.get("moneda", "ARS")
            url = item.get("url")

            cur = conn.execute(
                "INSERT INTO listings (run_id, product_type_id, titulo, precio, moneda, url) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, product_type_id, title, price, currency, url),
            )
            listing_id = cur.lastrowid

            conn.execute(
                "INSERT INTO ram (listing_id, capacidad_gb, ddr) VALUES (?, ?, ?)",
                (listing_id, item.get("capacidad"), item.get("ddr")),
            )
            count += 1

        conn.commit()

    print(f"[DB] {count} memorias RAM guardadas (run_id={run_id}) en {DB_PATH}")
    return count


# ----------------------------------------------------------------------------
# Consultas para reportes
# ----------------------------------------------------------------------------

def load_laptop_history_df():
    import pandas as pd

    with get_connection() as conn:
        df = pd.read_sql(
            """
            SELECT
                r.ejecutado_en AS timestamp,
                pr.nombre      AS proveedor,
                cl.marca       AS cpu_marca,
                cl.linea       AS cpu_linea,
                lp.ram_gb,
                lp.storage_gb,
                lp.storage_tipo,
                l.titulo,
                l.precio,
                l.moneda,
                l.url
            FROM listings l
            JOIN scrape_runs r ON l.run_id = r.id
            JOIN providers pr ON r.provider_id = pr.id
            JOIN laptops lp ON lp.listing_id = l.id
            LEFT JOIN cpu_line cl ON lp.cpu_line_id = cl.id
            WHERE l.product_type_id = (SELECT id FROM product_types WHERE slug = 'laptop')
            ORDER BY r.ejecutado_en
            """,
            conn,
            parse_dates=["timestamp"],
        )
    return df


def load_ram_history_df():
    import pandas as pd

    with get_connection() as conn:
        df = pd.read_sql(
            """
            SELECT
                r.ejecutado_en AS timestamp,
                pr.nombre      AS proveedor,
                rm.capacidad_gb,
                rm.ddr,
                l.titulo,
                l.precio,
                l.moneda,
                l.url
            FROM listings l
            JOIN scrape_runs r ON l.run_id = r.id
            JOIN providers pr ON r.provider_id = pr.id
            JOIN ram rm ON rm.listing_id = l.id
            WHERE l.product_type_id = (SELECT id FROM product_types WHERE slug = 'ram')
            ORDER BY r.ejecutado_en
            """,
            conn,
            parse_dates=["timestamp"],
        )
    return df


if __name__ == "__main__":
    init_db()
    print(f"Base inicializada en {DB_PATH}")
