FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para Playwright / Firefox
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    git \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libasound2-plugins \
    libatspi0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias de Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegador Playwright (Firefox)
RUN playwright install firefox

# Copiar el código del proyecto
COPY . .

ENV PYTHONPATH=/app

CMD ["bash"]
