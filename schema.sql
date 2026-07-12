-- ============================================================
-- schema.sql - Esquema de la base de precios (scraper.db)
-- Patrón: class table inheritance.
--   listings          = tabla base, común a TODO producto scrapeado.
--   laptops / ram      = tablas "hijas", 1 a 1 con listings via
--                        listing_id (mismo id, no autoincremental propio).
-- ============================================================

CREATE TABLE IF NOT EXISTS providers (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id    INTEGER NOT NULL REFERENCES providers(id),
    ejecutado_en   TEXT NOT NULL  -- ISO8601
);

CREATE TABLE IF NOT EXISTS product_types (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    slug    TEXT NOT NULL UNIQUE,   -- 'laptop', 'ram'
    nombre  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cpu_line (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    marca   TEXT NOT NULL,          -- 'AMD', 'Intel'
    linea   TEXT NOT NULL,          -- 'Ryzen 5', 'Core i5', 'Celeron'
    UNIQUE (marca, linea)
);

CREATE TABLE IF NOT EXISTS listings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           INTEGER NOT NULL REFERENCES scrape_runs(id),
    product_type_id  INTEGER NOT NULL REFERENCES product_types(id),
    titulo           TEXT NOT NULL,
    precio           REAL NOT NULL,
    moneda           TEXT NOT NULL,
    url              TEXT
);

CREATE TABLE IF NOT EXISTS laptops (
    listing_id    INTEGER PRIMARY KEY REFERENCES listings(id),
    cpu_line_id   INTEGER REFERENCES cpu_line(id),
    ram_gb        INTEGER,
    storage_gb    INTEGER,          -- NULL si no se pudo determinar con certeza
    storage_tipo  TEXT              -- 'SSD', 'HDD', 'NVMe'
);

CREATE TABLE IF NOT EXISTS ram (
    listing_id     INTEGER PRIMARY KEY REFERENCES listings(id),
    capacidad_gb   INTEGER,
    ddr            INTEGER          -- 4, 5, etc.
);

CREATE INDEX IF NOT EXISTS idx_listings_run_id ON listings(run_id);
CREATE INDEX IF NOT EXISTS idx_listings_product_type ON listings(product_type_id);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_provider ON scrape_runs(provider_id);
CREATE INDEX IF NOT EXISTS idx_laptops_cpu_line ON laptops(cpu_line_id);

-- ============================================================
-- Datos semilla (idempotentes: INSERT OR IGNORE)
-- ============================================================

INSERT OR IGNORE INTO providers (nombre) VALUES ('mercadolibre');
INSERT OR IGNORE INTO providers (nombre) VALUES ('compragamer');

INSERT OR IGNORE INTO product_types (slug, nombre) VALUES ('laptop', 'Notebook');
INSERT OR IGNORE INTO product_types (slug, nombre) VALUES ('ram', 'Memoria RAM');

INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('AMD', 'Ryzen 3');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('AMD', 'Ryzen 5');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('AMD', 'Ryzen 7');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('AMD', 'Ryzen 9');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('Intel', 'Celeron');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('Intel', 'Pentium');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('Intel', 'Core i3');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('Intel', 'Core i5');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('Intel', 'Core i7');
INSERT OR IGNORE INTO cpu_line (marca, linea) VALUES ('Intel', 'Core i9');
