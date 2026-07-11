#!/usr/bin/env python3
# Arma el HTML del reporte de precios de notebooks (última corrida en SQLite)
# para mandarlo por mail. Reemplaza el rol de json2html.py pero para los datos
# de MercadoLibre (que tienen forma distinta a los de RAM: no son categorías
# fijas, son N productos individuales + estadísticas + posibles gangas).

# Uso:
#     python3 ml_mail_report.py > /ruta/al/reporte.html
#     python3 ml_mail_report.py output.html

import sys
import statistics

from db import load_history_df


def format_currency(value) -> str:
    return f"${int(value):,}".replace(",", ".")


def compute_last_run_stats(df):
    if df.empty:
        return None, None, []

    last_ts = df["timestamp"].max()
    last_run = df[df["timestamp"] == last_ts]
    prices = sorted(last_run["price"].tolist())
    n = len(prices)

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
            last_run[last_run["price"] < lower_bound]
            .sort_values("price")
            .to_dict("records")
        )

    return last_ts, stats, gangas


def build_html(timestamp, stats, gangas) -> str:
    if stats is None:
        return "<p>No hay datos todavía en la base de notebooks.</p>"

    stats_rows = "".join(
        f"<tr><td>{label}</td><td class='number'>{format_currency(value)}</td></tr>"
        for label, value in [
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
            f"<tr><td>{format_currency(g['price'])}</td>"
            f"<td style='text-align:left'>{g['title']}</td></tr>"
            for g in gangas
        )
        gangas_html = f"""
        <h3 style="color:#2c3e50;">Posibles gangas ({len(gangas)})</h3>
        <table>
            <thead><tr><th>Precio</th><th>Producto</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

    return f"""
    <style>
        table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 12px; margin-bottom: 16px; }}
        th {{ background-color: #2c3e50; color: white; padding: 6px; text-align: center; }}
        td {{ padding: 6px; border: 1px solid #ddd; text-align: center; }}
        .number {{ font-family: monospace; }}
    </style>
    <p style="color:#6c757d;">Corrida: {timestamp} &middot; {stats['count']} publicaciones analizadas</p>
    <table>
        <thead><tr><th>Métrica</th><th>Valor (ARS)</th></tr></thead>
        <tbody>{stats_rows}</tbody>
    </table>
    {gangas_html}
    """


def wrap_email(body_html: str, title: str = "Reporte de Precios - Notebooks Ryzen 5") -> str:
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
    df = load_history_df()
    timestamp, stats, gangas = compute_last_run_stats(df)
    body = build_html(timestamp, stats, gangas)
    full_html = wrap_email(body)

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(full_html)
    else:
        print(full_html)


if __name__ == "__main__":
    main()
