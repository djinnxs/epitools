# 1. Usar una imagen base de Python más reciente
FROM python:3.10-slim

# ESTA ES LA CORRECCIÓN: Permite la instalación de la librería antigua 'sklearn'
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True
ENV LANG=C.UTF-8

# Variables de entorno CRÍTICAS para geopandas y pyodbc:
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV ACCEPT_GEOS=1

# 2. Copiar archivos y establecer el directorio de trabajo
COPY requirements.txt /app/requirements.txt
COPY . /app
WORKDIR /app

# 3. Instalar dependencias del sistema (apt-get)
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    curl \
    git \
    # Dependencias Geoespaciales: CRÍTICAS para GEOPANDAS
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    # Dependencias ODBC: CRÍTICAS para PYODBC
    unixodbc \
    unixodbc-dev \
    libxml2-dev \
    # Limpiamos el caché
    && rm -rf /var/lib/apt/lists/*

# 4. INSTALACIÓN FINAL
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Exponer y ejecutar
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
