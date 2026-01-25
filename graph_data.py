import json
import matplotlib.pyplot as plt
from datetime import datetime
import os

def load_data(filename):
    if not os.path.exists(filename):
        print(f"[-] Error: No se encontró el archivo {filename}")
        return None
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"[-] Error: El archivo {filename} está vacío o mal formado.")
            return None

def plot_prices(data):
    # Categorías que guardamos en el log
    categories = ['DDR4 16GB', 'DDR4 8GB', 'DDR5 16GB']
    # Colores consistentes para cada tipo
    colors = {'DDR4 16GB': '#3498db', 'DDR4 8GB': '#e67e22', 'DDR5 16GB': '#2ecc71'}
    
    # Extraer fechas y convertirlas a objetos datetime para que el eje X sea temporal
    dates = [datetime.strptime(entry['timestamp'], '%Y-%m-%d') for entry in data]
    
    fig, ax = plt.subplots(figsize=(12, 7))

    for cat in categories:
        # Extraer métricas para esta categoría
        meds = [entry[cat]['med'] for entry in data]
        stds = [entry[cat]['std'] for entry in data]
        mins = [entry[cat]['min'] for entry in data]
        maxs = [entry[cat]['max'] for entry in data]
        
        c = colors[cat]
        
        # 1. Bigotes (Rango total Min-Max) - Línea vertical fina
        ax.vlines(dates, mins, maxs, color=c, linestyle='-', alpha=0.3, linewidth=1)
        
        # 2. Caja (Desviación Estándar) - Barra centrada en la mediana
        # Representamos el área de mayor densidad de precios (Promedio +/- Std)
        bottoms = [m - s for m, s in zip(meds, stds)]
        heights = [2 * s for s in stds] # La caja mide 2 veces la desviación (una hacia arriba, otra abajo)
        
        ax.bar(dates, heights, bottom=bottoms, color=c, alpha=0.6, width=0.4, label=f'{cat} (Mediana ± SD)')
        
        # 3. Línea de tendencia (Mediana)
        ax.plot(dates, meds, color=c, marker='o', markersize=4, linestyle='--', linewidth=1, alpha=0.8)

    # Configuración estética del gráfico
    ax.set_title('Historial de Precios de Memorias RAM (Basado en Mediana y Desviación)', fontsize=14, pad=20)
    ax.set_ylabel('Precio en Pesos ($)', fontsize=12)
    ax.set_xlabel('Fecha de Consulta', fontsize=12)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()
    
    # Formatear el eje X para que no se amontonen las fechas
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Guardar el resultado
    output_name = 'reporte_precios.png'
    plt.savefig(output_name)
    print(f'[+] Gráfico generado exitosamente: {output_name}')

if __name__ == '__main__':
    log_file = 'prices.log'
    price_history = load_data(log_file)
    
    if price_history:
        if len(price_history) < 1:
            print("[-] No hay suficientes datos para graficar.")
        else:
            plot_prices(price_history)
