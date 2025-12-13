# Usamos una imagen base de Python más estable (3.9)
FROM python:3.9-slim

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

# 2. Copiar archivos de dependencias
COPY requirements.txt .

# 3. Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 4. Copiar TODO el contenido del proyecto
COPY . .

# 5. Exponer el puerto
EXPOSE 8501

# 6. Comando de inicio (Apuntando a app.py en la raíz)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
