import os
import sqlite3
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="PC Scraper API")

DB_PATH = Path(
    os.environ.get("SCRAPER_DB_PATH")
    or (Path(__file__).parent.parent / "db" / "scraper.db")
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/products")
def get_products():
    if not DB_PATH.exists():
        return []
    
    products = []
    with get_db() as conn:
        # RAM categories (ddr, capacidad_gb)
        ram_rows = conn.execute("""
            SELECT DISTINCT rm.ddr, rm.capacidad_gb
            FROM ram rm
            JOIN listings l ON rm.listing_id = l.id
            WHERE rm.ddr IS NOT NULL AND rm.capacidad_gb IS NOT NULL
        """).fetchall()
        for r in ram_rows:
            ddr = r["ddr"]
            cap = r["capacidad_gb"]
            products.append({
                "id": f"ram_ddr{ddr}_{cap}gb",
                "name": f"Memoria RAM DDR{ddr} {cap}GB",
                "type": "ram"
            })

        # Laptop categories (cpu marca, linea)
        laptop_rows = conn.execute("""
            SELECT DISTINCT cl.marca, cl.linea
            FROM laptops lp
            JOIN cpu_line cl ON lp.cpu_line_id = cl.id
        """).fetchall()
        for r in laptop_rows:
            marca = r["marca"]
            linea = r["linea"]
            slug_linea = linea.lower().replace(" ", "_")
            products.append({
                "id": f"laptop_{marca.lower()}_{slug_linea}",
                "name": f"Notebook {marca} {linea}",
                "type": "laptop"
            })

    return products

@app.get("/api/prices")
def get_prices(product_id: str = Query(...), days: str = Query("30")):
    if not DB_PATH.exists():
        return {"data": [], "stats": {"current": 0, "min_historic": 0, "var": 0}}

    with get_db() as conn:
        rows = []
        if product_id.startswith("ram_"):
            parts = product_id.replace("ram_ddr", "").split("_")
            if len(parts) == 2:
                ddr = int(parts[0])
                cap = int(parts[1].replace("gb", ""))
                rows = conn.execute("""
                    SELECT r.ejecutado_en AS timestamp, l.precio
                    FROM listings l
                    JOIN scrape_runs r ON l.run_id = r.id
                    JOIN ram rm ON rm.listing_id = l.id
                    WHERE rm.ddr = ? AND rm.capacidad_gb = ?
                    ORDER BY r.ejecutado_en ASC
                """, (ddr, cap)).fetchall()
        elif product_id.startswith("laptop_"):
            parts = product_id.replace("laptop_", "").split("_", 1)
            if len(parts) == 2:
                marca = parts[0].capitalize()
                linea_slug = parts[1]
                laptop_rows = conn.execute("""
                    SELECT r.ejecutado_en AS timestamp, l.precio, cl.linea
                    FROM listings l
                    JOIN scrape_runs r ON l.run_id = r.id
                    JOIN laptops lp ON lp.listing_id = l.id
                    JOIN cpu_line cl ON lp.cpu_line_id = cl.id
                    WHERE cl.marca = ?
                    ORDER BY r.ejecutado_en ASC
                """, (marca,)).fetchall()
                rows = [
                    r for r in laptop_rows 
                    if r["linea"].lower().replace(" ", "_") == linea_slug
                ]

    if not rows:
        return {"data": [], "stats": {"current": 0, "min_historic": 0, "var": 0}}

    runs_map = {}
    for r in rows:
        ts = r["timestamp"]
        price = r["precio"]
        if ts not in runs_map:
            runs_map[ts] = []
        runs_map[ts].append(price)

    sorted_ts = sorted(runs_map.keys())
    if days != "all":
        try:
            d_int = int(days)
            cutoff = datetime.now(timezone.utc) - timedelta(days=d_int)
            filtered_ts = []
            for ts in sorted_ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt >= cutoff:
                        filtered_ts.append(ts)
                except Exception:
                    filtered_ts.append(ts)
            sorted_ts = filtered_ts
        except ValueError:
            pass

    data_points = []
    all_prices = []
    for ts in sorted_ts:
        prices = sorted(runs_map[ts])
        n = len(prices)
        if n == 0:
            continue
        med = statistics.median(prices)
        std = statistics.stdev(prices) if n > 1 else 0.0
        mn = prices[0]
        mx = prices[-1]

        try:
            dt = datetime.fromisoformat(ts)
            epoch = int(dt.timestamp())
        except Exception:
            epoch = int(datetime.now().timestamp())

        data_points.append({
            "timestamp": epoch,
            "ts_str": ts,
            "mean": round(med, 2),
            "std": round(std, 2),
            "min": round(mn, 2),
            "max": round(mx, 2)
        })
        all_prices.extend(prices)

    current_price = data_points[-1]["mean"] if data_points else 0
    min_historic = min(all_prices) if all_prices else 0
    
    var = 0.0
    if len(data_points) >= 2:
        first_p = data_points[0]["mean"]
        last_p = data_points[-1]["mean"]
        if first_p > 0:
            var = round(((last_p - first_p) / first_p) * 100, 2)

    return {
        "data": data_points,
        "stats": {
            "current": current_price,
            "min_historic": min_historic,
            "var": var
        }
    }

frontend_dir = Path(__file__).parent
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="static")
