---
title: epitools
emoji: 📊
colorFrom: blue
colorTo: green
sdk: streamlit
app_file: app.sh # <--- ¡IMPORTANTE! Esto le dice que use app.sh para iniciar
---
# Análisis Epidemiológico en Streamlit

## Descripción
Este proyecto es un dashboard interactivo para análisis epidemiológico, construido con Streamlit. Utiliza datos de la base SNVS2 (SQL Server) para visualizar y analizar eventos de salud pública en Argentina. Incluye funcionalidades como mapas de casos y tasas, monitoreo de regularidad, predicciones temporales, integración con clima, scraping de noticias relacionadas con salud, chat IA para consultas de datos, y análisis avanzados (causal inference y ML forecasting).

El enfoque es en epidemiología general, con énfasis en reproducibilidad, seguridad y escalabilidad. Ideal para profesionales de salud pública, investigadores o analistas de datos.

## Características Principales
- **Dashboards Interactivos**: Filtros por provincia, departamento, evento, año y semana.
- **Visualizaciones**: Mapas choropleth (Folium/Plotly), gráficos temporales (línea/barra/área), pirámides poblacionales, corredores endémicos.
- **Cálculos Epidemiológicos**: Tasas por 100k habitantes, índices epidémicos, regularidad/oportunidad/cobertura.
- **Integraciones Externas**: Clima real-time/histórico (OpenWeather API), scraping de noticias salud (rumores epi), chat IA (OpenAI/PandasAI).
- **Predicciones y Avanzado**: Regresión lineal/Prophet para tendencias; causal inference (zepid); ML forecasting (EpiLearn).
- **Exportaciones**: CSV/Excel estilizados, PDF calendarios.
- **Seguridad**: Credenciales en .env; caching para eficiencia.

## Requisitos
- Python 3.8+
- Dependencias: Ver `requirements.txt` (instala con `pip install -r requirements.txt`).
- Base de datos: Acceso a SQL Server (SNVS2).
- APIs: Claves para OpenAI y OpenWeather en `.env`.

## Instalación
1. Clona el repositorio:
   ```
   git clone <url-del-repositorio>
   cd dashboard5-web
   ```

2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

3. Configura las variables de entorno:
   - Crea un archivo `.env` en la raíz del proyecto con las credenciales necesarias (ver `.env.example` si existe).

4. Genera los datos optimizados:
   - Ejecuta el script ETL para descargar y procesar los datos:
     ```
     python etl_semanal.py
     ```
   - Esto creará los archivos Parquet en `data/` necesarios para el funcionamiento del dashboard.

5. Ejecuta la aplicación:
   ```
   streamlit run Home.py
   ```

## Estructura del Proyecto
- `pages/`: Páginas individuales del dashboard.
- `utils/`: Utilidades comunes, incluyendo funciones para carga de datos.
- `data/`: Archivos de datos (Parquet, GeoJSON, etc.).
- `etl_semanal.py`: Script para extraer, transformar y cargar datos desde la base SQL.
- `requirements.txt`: Dependencias de Python.
