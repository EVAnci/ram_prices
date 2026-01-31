#!/usr/bin/env python3
"""
Script para convertir datos JSON de precios de memoria RAM a tabla HTML
Uso: python json_to_html_table.py input.json
     python json_to_html_table.py input.json output.html
"""

import json
import sys
from datetime import datetime


def format_currency(value):
    """Formatea números como moneda argentina"""
    return f"${value:,.2f}".replace(",", ".")


def json_to_html_table(data, include_styles=True):
    """
    Convierte el JSON de precios a una tabla HTML
    
    Args:
        data: diccionario con los datos
        include_styles: si True, incluye estilos CSS inline
    
    Returns:
        string con HTML de la tabla
    """
    
    # Estilos CSS para la tabla (compatibles con emails)
    styles = """
    <style>
        table {
            border-collapse: collapse;
            width: 100%;
            max-width: 600px;
            font-family: Arial, sans-serif;
            font-size: 14px;
        }
        th {
            background-color: #2c3e50;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        tr:hover {
            background-color: #e9ecef;
        }
        .number {
            text-align: right;
            font-family: 'Courier New', monospace;
        }
        .header-date {
            color: #6c757d;
            font-size: 12px;
            margin-bottom: 10px;
        }
    </style>
    """ if include_styles else ""
    
    # Extraer timestamp
    timestamp = data.get("timestamp", "")
    
    # Iniciar HTML
    html = f"{styles}\n"
    
    if timestamp:
        html += f'<p class="header-date">Fecha: {timestamp}</p>\n'
    
    html += '<table>\n'
    html += '  <thead>\n'
    html += '    <tr>\n'
    html += '      <th>Producto</th>\n'
    html += '      <th class="number">Máximo</th>\n'
    html += '      <th class="number">Mínimo</th>\n'
    html += '      <th class="number">Mediana</th>\n'
    html += '      <th class="number">Desv. Est.</th>\n'
    html += '    </tr>\n'
    html += '  </thead>\n'
    html += '  <tbody>\n'
    
    # Agregar filas para cada producto
    for product, stats in data.items():
        if product == "timestamp":
            continue
            
        html += '    <tr>\n'
        html += f'      <td><strong>{product}</strong></td>\n'
        html += f'      <td class="number">{format_currency(stats["max"])}</td>\n'
        html += f'      <td class="number">{format_currency(stats["min"])}</td>\n'
        html += f'      <td class="number">{format_currency(stats["med"])}</td>\n'
        html += f'      <td class="number">{format_currency(stats["std"])}</td>\n'
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
        print("Uso: python json_to_html_table.py input.json [output.html]")
        print("\nEjemplo de uso:")
        print("  python json_to_html_table.py datos.json")
        print("  python json_to_html_table.py datos.json reporte.html")
        sys.exit(1)
    
    input_json = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Leer JSON
    try:
        data = json.load(input_json)
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
