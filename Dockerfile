# 1. Usar una imagen base de Python más reciente y completa
FROM python:3.10-slim

# 2. Copiar archivos de dependencias y código ANTES de instalar dependencias
# Esto es esencial para el caching de Docker
COPY requirements.txt /app/requirements.txt
COPY . /app

# 3. Establecemos el directorio de trabajo
WORKDIR /app

# 4. Instalar dependencias del sistema (Incluyendo el compilador y dependencias GEO/ODBC)
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    curl \
    git \
    # Dependencias Geoespaciales
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    # Dependencias ODBC
    unixodbc \
    unixodbc-dev \
    libxml2-dev \
    # Limpiamos el caché
    && rm -rf /var/lib/apt/lists/*

# 5. Instalar dependencias de Python (PyStan ahora debería funcionar)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 6. Exponer el puerto
EXPOSE 8501

# 7. Comando de inicio
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
