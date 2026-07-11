#!/usr/bin/env python3
"""
Script para convertir datos JSON de precios de memoria RAM a tabla HTML
Uso: python json2html.py input.json
     python json2html.py input.json output.html
"""

import json
import sys
from datetime import datetime


def format_currency(value):
    """Formatea números como moneda argentina (versión compacta)"""
    # Formato compacto: $257800 en lugar de $257.800,00
    return f"${int(value)}"


def json_to_html_table(data, include_styles=True):
    """
    Convierte el JSON de precios a una tabla HTML
    Formato horizontal: productos en columnas, métricas en filas
    
    Args:
        data: diccionario con los datos
        include_styles: si True, incluye estilos CSS inline
    
    Returns:
        string con HTML de la tabla
    """
    
    # Estilos CSS para la tabla (optimizado para móvil)
    styles = """
    <style>
        table {
            border-collapse: collapse;
            width: 100%;
            font-family: Arial, sans-serif;
            font-size: 11px;
        }
        th {
            background-color: #2c3e50;
            color: white;
            padding: 6px 3px;
            text-align: center;
            font-weight: bold;
            font-size: 10px;
        }
        td {
            padding: 5px 3px;
            border: 1px solid #ddd;
            text-align: center;
            font-size: 10px;
        }
        td:first-child {
            background-color: #34495e;
            color: white;
            font-weight: bold;
            text-align: center;
            padding: 5px 4px;
        }
        .number {
            font-family: Arial, sans-serif;
            font-size: 10px;
        }
        .header-date {
            color: #6c757d;
            font-size: 10px;
            margin-bottom: 6px;
        }
    </style>
    """ if include_styles else ""
    
    # Extraer timestamp y productos
    timestamp = data.get("timestamp", "")
    products = {k: v for k, v in data.items() if k != "timestamp"}
    
    # Iniciar HTML
    html = f"{styles}\n"
    
    if timestamp:
        html += f'<p class="header-date">Fecha: {timestamp}</p>\n'
    
    html += '<table>\n'
    html += '  <thead>\n'
    html += '    <tr>\n'
    html += '      <th>Dato</th>\n'
    
    # Headers con nombres de productos (abreviados)
    for product in products.keys():
        # Simplificar nombres: "DDR4 16GB" -> "DDR4 16"
        short_name = product.replace('GB', '').strip()
        html += f'      <th>{short_name}</th>\n'
    
    html += '    </tr>\n'
    html += '  </thead>\n'
    html += '  <tbody>\n'
    
    # Filas de métricas
    metrics = [
        ('Máx', 'max'),
        ('Mín', 'min'),
        ('Med', 'med'),
        ('Std', 'std')
    ]
    
    for label, key in metrics:
        html += '    <tr>\n'
        html += f'      <td>{label}</td>\n'
        
        for stats in products.values():
            value = stats.get(key, 0)
            html += f'      <td class="number">{format_currency(value)}</td>\n'
        
        html += '    </tr>\n'
    
    html += '  </tbody>\n'
    html += '</table>\n'
    
    return html


def create_full_html_email(table_html, title="Reporte de Precios - Memorias RAM"):
    """Crea un HTML completo listo para email"""
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
        {table_html}
    </div>
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print("Uso: python json2html.py input.json [output.html]")
        print("\nEjemplo de uso:")
        print("  python json2html.py datos.json")
        print("  python json2html.py datos.json reporte.html")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Leer JSON
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{input_file}'")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: El archivo no contiene JSON válido - {e}")
        sys.exit(1)
    
    # Convertir a HTML
    table_html = json_to_html_table(data)
    full_html = create_full_html_email(table_html)
    
    # Guardar o mostrar
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"✓ Tabla HTML guardada en: {output_file}")
    else:
        print(full_html)


if __name__ == "__main__":
    main()
