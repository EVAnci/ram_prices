"""
Scraper de precios de notebooks en Mercado Libre. Versión Playwright,
guarda en el esquema normalizado (db.py / schema.sql).

Cambio de diseño clave respecto a versiones anteriores: la clasificación
de CPU/RAM/storage YA NO se infiere por título (regex por producto).
Se confía en el filtro de búsqueda de ML: cada URL en SCRAPE_TARGETS
declara explícitamente qué CPU/RAM/storage garantiza ese filtro, y esa
clasificación se aplica a TODOS los resultados de esa corrida.

Instalación:
    pip install -r requirements.txt
    playwright install firefox
"""

import re
import time
import random
import statistics
from dataclasses import dataclass, asdict
from typing import Optional

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright_stealth import Stealth

from db import db

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

# Formato de URL de ML:
# https://listado.mercadolibre.com.ar/computacion/notebooks-accesorios/
#                                                                       [patron-de-busqueda]_
#                                                                       Desde_[offset]_ (ausente si offset==0)
#                                                                       [filtro-de-precio]_
#                                                                       NoIndex_True_
#                                                                       PROCESSOR*LINE_[codigo]_
#                                                                       RAM*MEMORY*MODULE*TOTAL*CAPACITY_[NGB-*]_
#                                                                       SHIPPING*ORIGIN_[10215068]_
#                                                                       SSD*DATA*STORAGE*CAPACITY_[NGB-*]
BASE_URL = "https://listado.mercadolibre.com.ar/computacion/notebooks-accesorios/"
SEARCH_QUERY = "notebook"

# Cada target = una corrida de scraping con su propia clasificación.
# storage_gb queda en None a propósito: el filtro de ML garantiza un PISO
# (ej. "400GB-*" = 400GB o más), pero no la capacidad exacta de cada aviso,
# y no la extraemos del título porque no siempre aparece ahí.
SCRAPE_TARGETS = [
    {
        "cpu_marca": "AMD",
        "cpu_linea": "Ryzen 5",
        "ram_gb": 16,
        "storage_gb": None,
        "storage_tipo": "SSD",
        "filters": (
            "PriceRange_400000ARS-1500000ARS_NoIndex_True_"
            "PROCESSOR*LINE_2244215_"
            "RAM*MEMORY*MODULE*TOTAL*CAPACITY_16GB-*_"
            "SHIPPING*ORIGIN_10215068_"
            "SSD*DATA*STORAGE*CAPACITY_400GB-*"
        ),
    },
    # Agregá más targets acá (ej. Core i5, Ryzen 7) con su propia URL de
    # filtros armada navegando la web de ML, igual que con el primero.
]

RESULTS_PER_PAGE = 48
DELAY_BETWEEN_REQUESTS = 10.0
PAGE_TIMEOUT_MS = 300_000  # tiempo generoso para el Atom
MAX_RETRIES_ON_BLOCK = 2
RETRY_BACKOFF_SECONDS = 20.0

RESOURCES_TO_BLOCK = {"image", "font", "media", "stylesheet"}


@dataclass
class Product:
    title: str
    price: float
    currency: str
    url: Optional[str] = None


# ----------------------------------------------------------------------------
# CONSTRUCCIÓN DE URL
# ----------------------------------------------------------------------------

def build_page_url(filters: str, offset: int) -> str:
    if offset == 0:
        return f"{BASE_URL}{SEARCH_QUERY}_{filters}"
    return f"{BASE_URL}{SEARCH_QUERY}_Desde_{offset + 1}_{filters}"


def human_scroll(page):
    """Simula un usuario scrolleando hacia abajo leyendo los resultados."""
    for _ in range(random.randint(3, 6)):
        page.mouse.wheel(delta_x=0, delta_y=random.randint(300, 700))
        time.sleep(random.uniform(1, 2.5))


# ----------------------------------------------------------------------------
# SCRAPING
# ----------------------------------------------------------------------------

def is_blocked(html: str) -> bool:
    marker = "suspicious-traffic-frontend"
    return marker in html or "ingresa a tu cuenta" in html.lower()


def fetch(page, url: str):
    for attempt in range(1, MAX_RETRIES_ON_BLOCK + 2):
        try:
            page.goto(url, timeout=PAGE_TIMEOUT_MS)
            page.wait_for_selector(
                "li.ui-search-layout__item, div.ui-search-result__wrapper",
                timeout=PAGE_TIMEOUT_MS,
            )
            human_scroll(page)
        except PWTimeoutError:
            print(f"  [WARN] timeout cargando {url} o resolviendo el desafío JS.")
            return None

        html = page.content()

        if is_blocked(html):
            if attempt <= MAX_RETRIES_ON_BLOCK:
                print(
                    f"  [WARN] Muro anti-bot detectado (intento {attempt}), "
                    f"esperando {RETRY_BACKOFF_SECONDS}s antes de reintentar..."
                )
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            print("  [ERROR] Bloqueado tras reintentos, abortando esta página.")
            return None

        return page

    return None


def get_max_pages(page) -> int:
    el = page.query_selector("span.ui-search-search-result__quantity-results")
    if el is None:
        return 0
    results_quantity = int(el.inner_text().split(" ", 1)[0])
    return (results_quantity + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE - 1


def parse_price(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d]", "", text)
    return float(cleaned) if cleaned else None


def parse_listing(page) -> list[Product]:
    products: list[Product] = []
    cards = page.query_selector_all("li.ui-search-layout__item")

    for card in cards:
        title_el = (
            card.query_selector("h2.ui-search-item__title")
            or card.query_selector("a.poly-component__title")
            or card.query_selector("[class*='title']")
        )
        price_el = (
            card.query_selector("span.andes-money-amount__fraction")
            or card.query_selector("[class*='price'] [class*='fraction']")
        )
        link_el = card.query_selector("a[href]")

        if not title_el or not price_el:
            continue

        title = title_el.inner_text().strip()
        price = parse_price(price_el.inner_text())
        if price is None:
            continue

        products.append(
            Product(
                title=title,
                price=price,
                currency="ARS",
                url=link_el.get_attribute("href") if link_el else None,
            )
        )

    return products


def scrape_target(context, target: dict) -> list[Product]:
    all_products: list[Product] = []
    page = context.new_page()

    print(f"\n=== Scrapeando {target['cpu_marca']} {target['cpu_linea']} ===")
    page_num = 0
    max_pages = 0
    while page_num <= max_pages:
        offset = page_num * RESULTS_PER_PAGE
        url = build_page_url(target["filters"], offset)
        print(f"  Página {page_num + 1}: {url}")

        page = fetch(page, url)
        if page is None:
            print("  Sin más productos o bloqueado, cortando paginación.")
            break

        if page_num == 0:
            max_pages = get_max_pages(page)

        page_products = parse_listing(page)
        if not page_products:
            print("  Sin más productos, cortando paginación.")
            break

        print(f"  {len(page_products)} tarjetas.")
        all_products.extend(page_products)

        time.sleep(DELAY_BETWEEN_REQUESTS + 2.0)
        page_num += 1

    page.close()
    return all_products


def scrape_all() -> dict:
    """Devuelve {target_index: [Product, ...]}."""
    results: dict = {}

    with Stealth().use_sync(sync_playwright()) as pw:
        browser = pw.firefox.launch(headless=True)
        context = browser.new_context(
            locale="es-AR",
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
        )

        def route_handler(route):
            if route.request.resource_type in RESOURCES_TO_BLOCK:
                route.abort()
            else:
                route.continue_()

        context.route("**/*", route_handler)

        print("Generando sesión inicial en la página principal...")
        page = context.new_page()
        try:
            page.goto("https://www.mercadolibre.com.ar", timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            time.sleep(3)
        except PWTimeoutError:
            print("  [WARN] Timeout cargando la home, continuando de todos modos...")
        page.close()

        for i, target in enumerate(SCRAPE_TARGETS):
            results[i] = scrape_target(context, target)

        browser.close()

    return results


# ----------------------------------------------------------------------------
# ESTADÍSTICAS (solo para el resumen en consola/log de esta corrida)
# ----------------------------------------------------------------------------

def compute_stats(products: list[Product]) -> dict:
    if not products:
        return {"count": 0}

    prices = sorted(p.price for p in products)
    n = len(prices)
    stats = {
        "count": n,
        "mean": round(statistics.mean(prices), 2),
        "stdev": round(statistics.stdev(prices), 2) if n > 1 else 0.0,
        "min": prices[0],
        "max": prices[-1],
        "median": round(statistics.median(prices), 2),
    }
    if n >= 4:
        q1 = statistics.quantiles(prices, n=4)[0]
        q3 = statistics.quantiles(prices, n=4)[2]
        iqr = q3 - q1
        stats["lower_bound_ganga"] = round(q1 - 1.5 * iqr, 2)
    return stats


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main():
    db.init_db()

    all_results = scrape_all()

    with db.get_connection() as conn:
        run_id = db.start_run(conn, "mercadolibre")

    print("\n=== RESUMEN ===")
    for i, target in enumerate(SCRAPE_TARGETS):
        products = all_results.get(i, [])
        stats = compute_stats(products)
        print(f"{target['cpu_marca']} {target['cpu_linea']}: {stats}")

        db.save_laptop_listings(
            run_id=run_id,
            products=products,
            cpu_marca=target["cpu_marca"],
            cpu_linea=target["cpu_linea"],
            ram_gb=target["ram_gb"],
            storage_gb=target["storage_gb"],
            storage_tipo=target["storage_tipo"],
        )


if __name__ == "__main__":
    main()
