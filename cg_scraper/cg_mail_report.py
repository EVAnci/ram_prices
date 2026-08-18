#!/usr/bin/env python3
"""
Arma el HTML del reporte de precios de RAM (última corrida en SQLite) para
mandarlo por mail. Análogo a ml_mail_report.py, pero las estadísticas y la
detección de gangas se calculan POR CATEGORÍA (DDR + capacidad), no sobre
todo mezclado - una DDR4 8GB barata no es una "ganga", es una categoría
distinta con un piso de precio distinto.

Uso:
    python3 cg_mail_report.py > /ruta/al/reporte.html
    python3 cg_mail_report.py output.html
"""

import sys
import statistics

from db.db import load_ram_history


def format_currency(value) -> str:
    return f"${int(value):,}".replace(",", ".")


def compute_last_run_stats_ram(data):
    """
    Devuelve (timestamp, {"DDR4 8GB": {"stats": {...}, "gangas": [...]}, ...}).
    """
    if not data:
        return None, {}

    last_ts = max(item["timestamp"] for item in data)
    last_run = [
        item for item in data 
        if item["timestamp"] == last_ts and item.get("ddr") is not None and item.get("capacidad_gb") is not None
    ]

    grupos = {}
    keys = sorted(
        list({(item["ddr"], item["capacidad_gb"]) for item in last_run}),
        key=lambda x: (x[0], x[1])
    )

    for ddr, capacidad in keys:
        label = f"DDR{int(ddr)} {int(capacidad)}GB"

        subset = [item for item in last_run if item["ddr"] == ddr and item["capacidad_gb"] == capacidad]
        prices = sorted([item["precio"] for item in subset])
        n = len(prices)
        if n == 0:
            continue

        stats = {
            "count": n,
            "mean": statistics.mean(prices),
            "stdev": statistics.stdev(prices) if n > 1 else 0.0,
            "min": prices[0],
            "max": prices[-1],
            "median": statistics.median(prices),
        }

        gangas = []
        if n >= 4:
            q1 = statistics.quantiles(prices, n=4)[0]
            q3 = statistics.quantiles(prices, n=4)[2]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            gangas = sorted([item for item in subset if item["precio"] < lower_bound], key=lambda x: x["precio"])

        grupos[label] = {"stats": stats, "gangas": gangas}

    return last_ts, grupos


def build_category_html(label: str, stats: dict, gangas: list) -> str:
    stats_rows = "".join(
        f"<tr><td>{nombre}</td><td class='number'>{format_currency(valor)}</td></tr>"
        for nombre, valor in [
            ("Mínimo", stats["min"]),
            ("Máximo", stats["max"]),
            ("Media", stats["mean"]),
            ("Mediana", stats["median"]),
            ("Desvío estándar", stats["stdev"]),
        ]
    )

    gangas_html = ""
    if gangas:
        rows = "".join(
            f"<tr><td>{format_currency(g['precio'])}</td>"
            f"<td style='text-align:left'>{g['titulo']}</td></tr>"
            for g in gangas
        )
        gangas_html = f"""
        <p style="color:#c0392b; font-weight:bold; margin-bottom:4px;">
            {len(gangas)} posible(s) ganga(s)
        </p>
        <table>
            <thead><tr><th>Precio</th><th>Producto</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

    return f"""
    <h3 style="color:#2c3e50; border-bottom: 2px solid #eee; padding-bottom: 4px;">{label} ({stats['count']} publicaciones)</h3>
    <table>
        <thead><tr><th>Métrica</th><th>Valor (ARS)</th></tr></thead>
        <tbody>{stats_rows}</tbody>
    </table>
    {gangas_html}
    """


def build_html(timestamp, grupos: dict) -> str:
    if not grupos:
        return "<p>No hay datos todavía en la base de RAM.</p>"

    secciones = "".join(
        build_category_html(label, data["stats"], data["gangas"])
        for label, data in grupos.items()
    )

    return f"""
    <style>
        table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 12px; margin-bottom: 16px; }}
        th {{ background-color: #2c3e50; color: white; padding: 6px; text-align: center; }}
        td {{ padding: 6px; border: 1px solid #ddd; text-align: center; }}
        .number {{ font-family: monospace; }}
    </style>
    <p style="color:#6c757d;">Corrida: {timestamp}</p>
    {secciones}
    """


def wrap_email(body_html: str, title: str = "Reporte de Precios - Memoria RAM") -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 650px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2 style="color: #2c3e50; margin-top: 0;">{title}</h2>
        {body_html}
    </div>
</body>
</html>"""


def main():
    data = load_ram_history()
    timestamp, grupos = compute_last_run_stats_ram(data)
    body = build_html(timestamp, grupos)
    full_html = wrap_email(body)

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(full_html)
    else:
        print(full_html)


if __name__ == "__main__":
    main()
