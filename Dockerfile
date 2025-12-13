# Usamos una imagen base de Python ligera pero completa
FROM python:3.9-slim

# Establecemos el directorio de trabajo
WORKDIR /app

# 1. Instalar dependencias del sistema (CRUCIAL para pyodbc, geopandas y compilación)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    unixodbc \
    unixodbc-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 2. Copiar archivos de dependencias
COPY requirements.txt .

# 3. Instalar dependencias de Python
# Actualizamos pip para evitar advertencias y errores de compilación
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 4. Copiar TODO el contenido del proyecto al contenedor
# (Esto incluye app.py, carpetas pages/, utils/, data/, etc.)
COPY . .

# 5. Exponer el puerto de Streamlit
EXPOSE 8501

# 6. Chequeo de salud (Opcional pero recomendado por HF)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 7. Comando de inicio CORRECTO
# Apuntamos directamente al archivo app.py en la raíz (/app/app.py)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
