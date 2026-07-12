"""
Genera un reporte histórico a partir de precios_notebooks.db:
- Gráfico de caja y bigotes (boxplot) de precios agrupados por fecha de corrida.
- Serie de media +/- desvío estándar a lo largo del tiempo, superpuesta.
- Un resumen en consola con la tendencia (¿sube o baja la media reciente?).

Uso:
    python generate_report.py
Genera: reporte_precios.png
"""

import matplotlib
matplotlib.use("Agg")  # sin entorno de escritorio en el server, no hace falta X
import matplotlib.pyplot as plt
import pandas as pd

from db import load_laptop_history_df

OUTPUT_IMG = "reporte_precios.png"


def main():
    df = load_laptop_history_df()

    if df.empty:
        print("No hay datos en la base todavía. Corré el scraper primero.")
        return

    # Agrupamos por fecha (día) de la corrida, no por timestamp exacto,
    # para que varias corridas del mismo día se vean como una sola caja.
    df["fecha"] = df["timestamp"].dt.date

    fechas_ordenadas = sorted(df["fecha"].unique())
    datos_por_fecha = [df.loc[df["fecha"] == f, "precio"].values for f in fechas_ordenadas]

    resumen = df.groupby("fecha")["precio"].agg(["mean", "std", "min", "max", "count"])
    print("=== Resumen por fecha ===")
    print(resumen)

    # Tendencia simple: comparar media de la corrida más reciente vs la anterior
    if len(resumen) >= 2:
        ultima = resumen.iloc[-1]["mean"]
        anterior = resumen.iloc[-2]["mean"]
        variacion = ((ultima - anterior) / anterior) * 100
        direccion = "subió" if variacion > 0 else "bajó"
        print(f"\nLa media {direccion} un {abs(variacion):.1f}% respecto a la corrida anterior.")

    # --- Gráfico ---
    fig, ax = plt.subplots(figsize=(max(8, len(fechas_ordenadas) * 1.2), 6))

    ax.boxplot(
        datos_por_fecha,
        tick_labels=[f.isoformat() for f in fechas_ordenadas],
        showmeans=True,
    )

    ax.set_title("Distribución de precios de notebooks (Ryzen 5 / 16GB / 400GB+ SSD)")
    ax.set_xlabel("Fecha de corrida")
    ax.set_ylabel("Precio (ARS)")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(OUTPUT_IMG, dpi=150)
    print(f"\nGráfico guardado en {OUTPUT_IMG}")


if __name__ == "__main__":
    main()
