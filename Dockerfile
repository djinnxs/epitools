# Usamos una imagen base de Python más estable (3.9)
FROM python:3.9-slim

# COPIAR ARCHIVOS AL CONTEXTO ANTES DE SETEAR EL WORKDIR
# Si este paso falla, es que el repositorio Git no está sincronizado
COPY . /app
COPY requirements.txt /app/requirements.txt

# Establecemos el directorio de trabajo
WORKDIR /app

# 1. Instalar dependencias del sistema (Lista COMPLETA y CORRECTA)
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

# 3. Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 5. Exponer el puerto
EXPOSE 8501

# 6. Comando de inicio
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
