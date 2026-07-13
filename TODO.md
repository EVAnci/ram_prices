# TODO: Refactorización y Normalización de Base de Datos (v2)

Este documento detalla la reestructuración de la base de datos para separar los atributos estáticos de los productos (título, especificaciones, URL) de sus datos móviles (historial de precios en el tiempo).

## Objetivos
- **Eliminar redundancia:** Evitar duplicar textos largos (`titulo`, `url`) y especificaciones en cada corrida de scraping.
- **Optimizar almacenamiento:** Reducir el crecimiento de la base de datos a largo plazo.
- **Mantener historial limpio:** Almacenar solo el precio y la fecha de captura por cada registro de tiempo.

---

## Nuevo Diseño del Esquema

La idea es mover los datos de `listings` que nunca cambian a una tabla `products`. El precio se moverá a una nueva tabla `price_history`.

```sql
-- 1. Tabla de Productos Únicos (Datos Estáticos)
CREATE TABLE IF NOT EXISTS products (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    product_type_id  INTEGER NOT NULL REFERENCES product_types(id),
    provider_id      INTEGER NOT NULL REFERENCES providers(id),
    titulo           TEXT NOT NULL,
    url              TEXT UNIQUE NOT NULL -- La URL será nuestra clave única
);

-- 2. Especificaciones de Laptops (Relación 1 a 1 con products)
CREATE TABLE IF NOT EXISTS product_laptops (
    product_id    INTEGER PRIMARY KEY REFERENCES products(id),
    cpu_line_id   INTEGER REFERENCES cpu_line(id),
    ram_gb        INTEGER,
    storage_gb    INTEGER,
    storage_tipo  TEXT
);

-- 3. Especificaciones de RAM (Relación 1 a 1 con products)
CREATE TABLE IF NOT EXISTS product_ram (
    product_id     INTEGER PRIMARY KEY REFERENCES products(id),
    capacidad_gb   INTEGER,
    ddr            INTEGER
);

-- 4. Historial de Precios (La que va a crecer todos los días)
CREATE TABLE IF NOT EXISTS price_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    run_id      INTEGER NOT NULL REFERENCES scrape_runs(id), -- Mantiene la relación con la corrida y el timestamp
    precio      REAL NOT NULL,
    moneda      TEXT NOT NULL
);
```

---

## Plan de Migración de Datos

Cuando decidamos aplicar este cambio, podremos migrar todos los datos que se hayan acumulado en el formato viejo ejecutando este plan de acción mediante un script SQL o Python:

### Paso 1: Crear las nuevas tablas temporales
Crear las tablas `products`, `product_laptops`, `product_ram` y `price_history` utilizando sufijos temporales (ej. `new_products`).

### Paso 2: Migrar los Productos Únicos
Agrupamos todas nuestras publicaciones viejas por `url` única e insertamos los registros en la nueva tabla:
```sql
INSERT INTO new_products (product_type_id, provider_id, titulo, url)
SELECT DISTINCT l.product_type_id, r.provider_id, l.titulo, l.url
FROM listings l
JOIN scrape_runs r ON l.run_id = r.id
WHERE l.url IS NOT NULL;
```

### Paso 3: Migrar las Especificaciones Estáticas
Para las laptops y memorias RAM, migramos una única especificación técnica por cada producto creado vinculándolo mediante su URL:
```sql
-- Para Laptops
INSERT INTO new_product_laptops (product_id, cpu_line_id, ram_gb, storage_gb, storage_tipo)
SELECT DISTINCT np.id, lp.cpu_line_id, lp.ram_gb, lp.storage_gb, lp.storage_tipo
FROM laptops lp
JOIN listings l ON lp.listing_id = l.id
JOIN new_products np ON l.url = np.url;

-- Para RAMs
INSERT INTO new_product_ram (product_id, capacidad_gb, ddr)
SELECT DISTINCT np.id, rm.capacidad_gb, rm.ddr
FROM ram rm
JOIN listings l ON rm.listing_id = l.id
JOIN new_products np ON l.url = np.url;
```

### Paso 4: Migrar el Historial de Precios
Pasamos todas las "observaciones" de precio que teníamos en `listings` a la tabla de historial, vinculándolas a su respectivo `product_id` nuevo:
```sql
INSERT INTO new_price_history (product_id, run_id, precio, moneda)
SELECT np.id, l.run_id, l.precio, l.moneda
FROM listings l
JOIN new_products np ON l.url = np.url;
```

### Paso 5: Reemplazo de tablas
1. Borrar las tablas viejas (`laptops`, `ram`, `listings`).
2. Renombrar las tablas nuevas (quitar el prefijo `new_`).
3. Recrear los índices necesarios.

---

## Cambios Requeridos en el Código (`db.py`)

Cuando hagamos la migración, las funciones de guardado en `db.py` tendrán que modificarse para seguir esta lógica:

1. **Buscar o Crear Producto:**
   Al procesar un producto scrapeado, primero hacer un `SELECT id FROM products WHERE url = ?`.
   - Si no existe: Hacer `INSERT INTO products ...` y luego insertar sus especificaciones en `product_laptops` o `product_ram`. Obtener el `product_id` generado.
   - Si existe: Obtener directamente el `product_id`.

2. **Verificación de duplicado de precio (Opcional pero recomendado):**
   - Buscar el último precio registrado para ese `product_id`.
   - Si el precio cambió en comparación con la última corrida, o si es la primera corrida del día, insertar una nueva fila en `price_history`.

3. **Insertar en Historial:**
   - Hacer un `INSERT INTO price_history (product_id, run_id, precio, moneda) ...`.

4. **Actualizar consultas de Reportes (`load_..._history_df`):**
   Actualizar los `JOIN` en las funciones de Pandas para que consuman desde `price_history` y `products` en vez de `listings`.

---

## Fase: Servidor Django Local & Panel de Control "Bolsa Económica"

El objetivo de esta fase es crear una interfaz web local para monitorear los precios como si fuera un tablero de acciones financieras, facilitando la exportación de datos hacia la computadora de análisis personal.

### 1. Dashboard de Visualización
*   **Integración con Pandas:** Aprovechar las funciones actuales `load_laptop_history_df` y `load_ram_history_df` dentro de las Views de Django para procesar los datos rápidamente.
*   **Gráficos Interactivos:** Implementar una librería frontend como **Chart.js** o **Plotly** para ver curvas de evolución de precios, alertas de "Mínimo Histórico" y detectar fluctuaciones sospechosas (falsas ofertas).
*   **Filtros Avanzados:** Crear vistas para filtrar por características clave (ej. "Solo laptops Ryzen 5 con 16GB RAM" o "Memorias DDR4 por proveedor").

### 2. Sincronización y Descarga de Datos
*   **Endpoint de Descarga:** Crear una ruta protegida en Django (ej. `/api/download-db/`) que empaquete y permita descargar el archivo `scraper.db` actual en un click.
*   **Script de Sincronización Local:** Desarrollar un script corto en la PC potente que descargue automáticamente el archivo SQLite del servidor (vía `scp` o mediante el endpoint de Django) para actualizar el entorno de análisis local sin tocar la base de datos de producción.

### 3. Hoja de Ruta: Migración a MariaDB
Cuando el volumen de datos crezca o se requiera acceso concurrente directo desde ambas computadoras sin mover archivos, se migrará de SQLite a MariaDB:
*   **Configuración en Django:** Cambiar el `DATABASES` en `settings.py` de `sqlite3` a `mysql` (MariaDB). Gracias al ORM de Django, este cambio es casi transparente para la aplicación web.
*   **Migración de Datos:** Utilizar herramientas como `django-dumpdata` / `loaddata` o un script de volcado SQL para mover el historial acumulado.

### 4. Algoritmo de Predicción
*   **Aislamiento de Carga:** Correr los Jupyter Notebooks y scripts de Machine Learning (ej. Regresión Lineal, Modelos de Series Temporales como ARIMA o Prophet) *únicamente* en la PC de escritorio potente para no saturar el servidor de scraping.
*   **Dataset de Entrenamiento:** El servidor Django local proveerá los datos limpios y normalizados listos para entrenar los modelos predictivos de manera periódica.
