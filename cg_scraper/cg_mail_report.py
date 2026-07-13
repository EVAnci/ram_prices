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

from db.db import load_ram_history_df


def format_currency(value) -> str:
    return f"${int(value):,}".replace(",", ".")


def compute_last_run_stats_ram(df):
    """
    Devuelve (timestamp, {"DDR4 8GB": {"stats": {...}, "gangas": [...]}, ...}).

    Agrupa por (ddr, capacidad_gb) ANTES de calcular cuartiles/IQR, así el
    límite de "ganga" de cada categoría se calcula contra su propia
    distribución de precios, no contra el resto de las categorías.
    """
    if df.empty:
        return None, {}

    last_ts = df["timestamp"].max()
    last_run = df[df["timestamp"] == last_ts].dropna(subset=["ddr", "capacidad_gb"])

    grupos = {}
    # sort_values asegura un orden estable y prolijo en el mail (DDR4 8, DDR4 16, DDR5 16...)
    claves = last_run[["ddr", "capacidad_gb"]].drop_duplicates().sort_values(["ddr", "capacidad_gb"])

    for _, row in claves.iterrows():
        ddr, capacidad = row["ddr"], row["capacidad_gb"]
        label = f"DDR{int(ddr)} {int(capacidad)}GB"

        subset = last_run[(last_run["ddr"] == ddr) & (last_run["capacidad_gb"] == capacidad)]
        prices = sorted(subset["precio"].tolist())
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
            gangas = (
                subset[subset["precio"] < lower_bound]
                .sort_values("precio")
                .to_dict("records")
            )

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
    df = load_ram_history_df()
    timestamp, grupos = compute_last_run_stats_ram(df)
    body = build_html(timestamp, grupos)
    full_html = wrap_email(body)

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(full_html)
    else:
        print(full_html)


if __name__ == "__main__":
    main()
