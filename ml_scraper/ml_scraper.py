# Scraper de precios de notebooks (Ryzen 5, 16GB RAM, ~400GB+ SSD) en Mercado Libre.
# Versión Playwright (navegador real headless) - pensada para correr en hardware
# modesto (ej. Atom N2500, sin entorno de escritorio) 1-2 veces al día.

# Por qué Playwright y no requests/BeautifulSoup:
# Mercado Libre tiene un sistema anti-bot ("suspicious-traffic-frontend") que
# detecta clientes no-browser por fingerprint TLS y desafíos JS. Un navegador
# real headless resuelve ambos problemas de forma nativa.

# Optimizaciones para hardware débil:
# - Se bloquean imágenes/fuentes/CSS/media (no se necesitan para el texto).
# - Un solo browser, un solo context, sin paralelismo.
# - Se usa Firefox (más liviano que Chromium en general).

# Instalación:
#     pip install playwright
#     pip install playwright-stealth
#     playwright install firefox

import json
import re
import time
import statistics
from dataclasses import dataclass, asdict
from typing import Optional
import random

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright_stealth import Stealth

from db import init_db, save_run

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

# Formato de URL de ML:
# https://listado.mercadolibre.com.ar/computacion/notebooks-accesorios/
#                                                                       [patron-de-busqueda]_
#                                                                       Desde_[offset]_ (ausente si offset==0)
#                                                                       [filtro-de-precio]_
#                                                                       NoIndex_True_
#                                                                       PROCESSOR*LINE_[2244215=AMD Ryzen 5]_
#                                                                       RAM*MEMORY*MODULE*TOTAL*CAPACITY_[16GB-*]_
#                                                                       SHIPPING*ORIGIN_[10215068]_
#                                                                       SSD*DATA*STORAGE*CAPACITY_[400GB-*]
BASE_URL = "https://listado.mercadolibre.com.ar/computacion/notebooks-accesorios/"
SEARCH_QUERY = "notebook"
FILTERS = (
    "PriceRange_400000ARS-1500000ARS_NoIndex_True_"
    "PROCESSOR*LINE_2244215_"
    "RAM*MEMORY*MODULE*TOTAL*CAPACITY_16GB-*_"
    "SHIPPING*ORIGIN_10215068_"
    "SSD*DATA*STORAGE*CAPACITY_400GB-*"
)

RESULTS_PER_PAGE = 48
DELAY_BETWEEN_REQUESTS = 10.0  # segundos entre páginas
PAGE_TIMEOUT_MS = 300_000 # Tiempo generoso para el atom
MAX_RETRIES_ON_BLOCK = 2
RETRY_BACKOFF_SECONDS = 20.0

# Script para reducir señales obvias de automatización (navigator.webdriver, etc.)
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['es-AR', 'es'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
"""

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


def human_scroll(page):
    """Simula un usuario scrolleando hacia abajo leyendo los resultados."""
    scroll_steps = random.randint(3, 6)
    
    for _ in range(scroll_steps):
        # Scrollea hacia abajo entre 300 y 700 píxeles por vez
        pixels = random.randint(300, 700)
        page.mouse.wheel(delta_x=0, delta_y=pixels)
        
        # Pausa aleatoria entre cada movimiento del dedo/mouse
        time.sleep(random.uniform(1, 2.5))

def build_page_url(offset: int) -> str:
    if offset == 0:
        return f"{BASE_URL}{SEARCH_QUERY}_{FILTERS}"
    return f"{BASE_URL}{SEARCH_QUERY}_Desde_{offset + 1}_{FILTERS}"


# ----------------------------------------------------------------------------
# SCRAPING
# ----------------------------------------------------------------------------

def is_blocked(html: str) -> bool:
    marker = "suspicious-traffic-frontend"
    return marker in html or "ingresa a tu cuenta" in html.lower()


def fetch(page, url: str) -> Optional[list[Product]]:
    for attempt in range(1, MAX_RETRIES_ON_BLOCK + 2):
        try:
            # Quitamos el wait_until="domcontentloaded", dejamos que Playwright use 
            # su comportamiento por defecto (esperar al evento 'load')
            page.goto(url, timeout=PAGE_TIMEOUT_MS)
            
            # ¡LA CLAVE!: Forzamos a Playwright a esperar a que el desafío JS 
            # termine y renderice las tarjetas de producto.
            page.wait_for_selector("li.ui-search-layout__item, div.ui-search-result__wrapper", timeout=PAGE_TIMEOUT_MS)
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

def get_max_pages(page):
    results = page.query_selector("span.ui-search-search-result__quantity-results").inner_text()
    results_quantity = int(results.split(' ', 1)[0])
    pages = (results_quantity + RESULTS_PER_PAGE-1) // RESULTS_PER_PAGE - 1
    return pages

def parse_listing(page) -> list[Product]:
    products: list[Product] = []

    # Selector principal + fallbacks, evaluados en el propio DOM del browser.
    cards = page.query_selector_all("li.ui-search-layout__item")

    for card in cards:
        title_el = (
            card.query_selector("h2.ui-search-item__title")
            or card.query_selector("a.poly-component__title")
            or card.query_selector("[class*='title']")
        )
        price_el = card.query_selector("div.poly-price__current span.andes-money-amount__fraction")
        

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


def parse_price(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d]", "", text)
    if not cleaned:
        return None
    return float(cleaned)


def scrape_all() -> list[Product]:
    all_products: list[Product] = []

    # Envolvemos sync_playwright() con Stealth().use_sync()
    with Stealth().use_sync(sync_playwright()) as pw:
        
        browser = pw.firefox.launch(headless=True)
        context = browser.new_context(
            locale="es-AR",
            viewport={'width': 1366, 'height': 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
        )
        
        # Bloqueo de recursos para aliviar el procesador Atom
        def route_handler(route):
            if route.request.resource_type in RESOURCES_TO_BLOCK:
                route.abort()
            else:
                route.continue_()

        context.route("**/*", route_handler)

        page = context.new_page()
        
        # Ya no hace falta llamar a ninguna función stealth aquí abajo. 
        # La sesión ya está "parcheada" de forma automática.

        # --- CONSTRUCCIÓN DE SESIÓN ---
        print("Generando sesión inicial en la página principal...")
        try:
            page.goto("https://www.mercadolibre.com.ar", timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            time.sleep(3)
        except PWTimeoutError:
            print("  [WARN] Timeout cargando la home, continuando de todos modos...")

        # --- INICIO DEL SCRAPING REAL ---
        min_pages = 1
        max_pages = min_pages
        page_num = 0
        while page_num <= max_pages:
            offset = page_num * RESULTS_PER_PAGE
            url = build_page_url(offset)
            print(f"\nPágina {page_num + 1}: {url}")

            page = fetch(page, url)
            if page_num == 0: # En la primera iteración, encontramos la cantidad de resultados y calculamos las paginas
                max_pages = get_max_pages(page)
            page_products = parse_listing(page)
            if not page_products:
                print("  Sin más productos o bloqueado, cortando paginación.")
                break

            print(f"  {len(page_products)} tarjetas.")
            all_products.extend(page_products)

            time.sleep(DELAY_BETWEEN_REQUESTS + 2.0)
            page_num+=1

        browser.close()

    return all_products


# ----------------------------------------------------------------------------
# ESTADÍSTICAS + DETECCIÓN DE GANGAS (outliers bajos)
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
        lower_bound = q1 - 1.5 * iqr
        stats["q1"] = round(q1, 2)
        stats["q3"] = round(q3, 2)
        stats["iqr"] = round(iqr, 2)
        stats["lower_bound_ganga"] = round(lower_bound, 2)

    return stats


def find_gangas(products: list[Product], stats: dict) -> list[dict]:
    """Productos por debajo del límite inferior del IQR: candidatos a 'ganga'."""
    if "lower_bound_ganga" not in stats:
        return []
    bound = stats["lower_bound_ganga"]
    return [asdict(p) for p in products if p.price < bound]


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------


def main():
    products = scrape_all()
    stats = compute_stats(products)
    gangas = find_gangas(products, stats)

    init_db()
    save_run(products)

    results = {
        "products": [asdict(p) for p in products],
        "stats": stats,
        "posibles_gangas": gangas,
    }

    output_path = "resultados_notebooks_ml.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n=== RESUMEN ===")
    print(stats)
    if gangas:
        print(f"\n{len(gangas)} posible(s) ganga(s) (precio atípicamente bajo):")
        for g in gangas:
            print(f"  ${g['price']:,.0f} - {g['title']}")
    print(f"\nGuardado en {output_path}")


if __name__ == "__main__":
    main()
