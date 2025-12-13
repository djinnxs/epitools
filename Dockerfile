# 1. Usar una imagen base de Python más reciente y completa
FROM python:3.10-slim

# Establecer la variable de entorno para evitar advertencias de localización
ENV LANG=C.UTF-8

# 2. Copiar archivos de dependencias y código ANTES de instalar dependencias
COPY requirements.txt /app/requirements.txt
COPY . /app

# 3. Establecemos el directorio de trabajo
WORKDIR /app

# 4. Instalar SÓLO el compilador y dependencias del sistema
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

# 5. Instalar dependencias de Python (Debería funcionar con el compilador ya listo)
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. Exponer el puerto
EXPOSE 8501

# 7. Comando de inicio
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
