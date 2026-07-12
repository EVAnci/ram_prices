"""
Scraper de precios de memoria RAM en compragamer.com (API expuesta, sin
necesidad de Playwright). Misma lógica de scraping que la versión original
(market.py), adaptada para guardar en el esquema SQLite normalizado en vez
de un JSON acumulativo.
"""

from statistics import median, stdev
import requests

from db import db

LOG_LEVEL = 0  # 1 = más verboso

url_catalog = "https://static.compragamer.com/armado_pc_caracteristicas"
url_products = "https://static.compragamer.com/productos"

# DDR como entero (charlado en el diseño): 'DDR4' -> 4, 'DDR5' -> 5
DDR_MAP = {"DDR4": 4, "DDR5": 5}


def clean_mem(mem: dict, secondary: bool = False) -> None:
    """Elimina claves no usadas de un dict de memoria (in-place)."""
    if secondary:
        unused_keys = [
            "precios_cuotas", "imagenes", "precioListaAnterior",
            "precioEspecialAnterior", "garantia", "garantia_oficial",
            "busca_en_ml", "precioEspecialCombo", "iva",
            "impuesto_interno_importacion", "precioListaCombo",
            "id_nivel_falla", "descripcion_falla", "tipo_falla", "promocion",
        ]
    else:
        unused_keys = [
            "disipador", "sodimm", "w", "slot", "activo", "latencia_cl",
            "disipacion_alta", "es_cudimm", "marca", "voltaje",
        ]

    for key in unused_keys:
        mem.pop(key, None)  # pop con default: no explota si la clave no está


def get_price():
    catalog = requests.get(url_catalog, timeout=15)
    catalog.raise_for_status()
    mems = catalog.json().get("mem", [])

    products = requests.get(url_products, timeout=15)
    products.raise_for_status()
    products_data = products.json()

    tempmem = mems.copy()
    product_mems = []
    for product in products_data:
        if not tempmem:
            break
        for i, mem in enumerate(tempmem):
            if product.get("id_producto") == mem.get("id_producto"):
                tempmem.pop(i)
                product_mems.append(product)
                break

    ddr416, ddr48, ddr516 = [], [], []
    for mem in mems:
        clean_mem(mem) # return void. Here mem is passed by reference
        for product in product_mems:
            # The number 15 is to get the DIMM type of memory. Remove if want DIMM and SODIMM. Use 47 if just SODIMM

            if (
                mem.get("id_producto") == product.get("id_producto")
                and product.get("id_subcategoria") == 15
            ):            
                # This shows the complete list shown of the page catalog
                # clean_mem(product,True)
                # print(dumps(product,indent=2))
                mem["precio"] = product.get("precioEspecial")
                mem["nombre"] = product.get("nombre")
                mem["stock"] = product.get("stock")

                tipo = mem.get("tipo")
                capacidad = mem.get("capacidad")
                if tipo == "DDR4" and capacidad == 16:
                    ddr416.append(mem)
                elif tipo == "DDR4" and capacidad == 8:
                    ddr48.append(mem)
                elif tipo == "DDR5" and capacidad == 16:
                    ddr516.append(mem)

    return ddr416, ddr48, ddr516


def to_listing_items(mems: list, ddr: int) -> list:
    """Convierte la lista de dicts de compragamer al formato que espera db.save_ram_listings."""
    items = []
    for mem in mems:
        if mem.get("precio") is None:
            continue
        items.append(
            {
                "nombre": mem.get("nombre", ""),
                "precio": mem["precio"],
                "moneda": "ARS",
                "capacidad": mem.get("capacidad"),
                "ddr": ddr,
                "url": None,  # compragamer no expone URL directa en este endpoint
            }
        )
    return items


def main():
    db.init_db()

    ddr416, ddr48, ddr516 = get_price()

    with db.get_connection() as conn:
        run_id = db.start_run(conn, "compragamer")

    all_items = (
        to_listing_items(ddr416, ddr=4)
        + to_listing_items(ddr48, ddr=4)
        + to_listing_items(ddr516, ddr=5)
    )

    if not all_items:
        print("[WARN] No se encontraron memorias RAM para guardar.")
        return

    db.save_ram_listings(run_id, all_items)

    if LOG_LEVEL == 1:
        for label, mems in [("DDR4 16GB", ddr416), ("DDR4 8GB", ddr48), ("DDR5 16GB", ddr516)]:
            prices = [m["precio"] for m in mems if m.get("precio") is not None]
            if prices:
                print(
                    f"{label}: min={min(prices)} max={max(prices)} "
                    f"med={median(prices)} std={round(stdev(prices), 2) if len(prices) > 1 else 0}"
                )


if __name__ == "__main__":
    main()
