# Dashboard de Análisis Epidemiológico Nacional (Argentina)

Este proyecto es una herramienta integral de visualización y análisis epidemiológico desarrollada con **Streamlit**. Está diseñada para monitorear, analizar y predecir eventos de salud pública a nivel nacional (Argentina).

## Características Principales

- **Dashboards Interactivos**: Visualización dinámica de casos filtrables por Año, Evento, Provincia y Grupo Etario.
- **Mapas Geoespaciales**:
  - **Nivel Nacional**: Mapa de calor por provincias.
  - **Nivel Departamental**: Desglose por departamentos dentro de cada provincia.
- **Análisis Temporal**:
  - **Corredores Endémicos**: Visualización de zonas de seguridad, éxito, alarma y brote.
  - **Tendencias y Predicciones**: Modelos avanzados (Prophet, SARIMA) para proyectar casos futuros.
  - **Nowcasting**: Estimación de casos en tiempo real corrigiendo el retraso de notificación.
- **Sistema de Alertas Tempranas (EWS)**: Escaneo automático de toda la base para detectar brotes.
- **Información Contextual**:
  - **Clima**: Integración con datos climáticos históricos y actuales.
  - **Rumores**: Web scraping de noticias de salud para detección temprana de alertas.
  - **Epidemiología IA**: Consultas en lenguaje natural sobre la base de datos.
- **Reportes**: Generación automática de calendarios epidemiológicos en PDF y exportación de datos a Excel.

## Requisitos del Sistema

- **Python 3.12** o superior.
- **Git** (para clonar el repositorio).
- Acceso a internet (para mapas y descargas de datos).

## Instalación

1.  **Clonar el repositorio**:

    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd epitools
    ```

2.  **Crear un entorno virtual**:

    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate  # Windows
    source .venv/bin/activate  # Linux/Mac
    ```

3.  **Instalar dependencias**:

    ```bash
    pip install -r requirements.txt
    ```

    > **Nota**: `weasyprint` puede requerir librerías adicionales del sistema (GTK) en Windows.

## Configuración

Crea un archivo `.env` en la raíz del proyecto:

```env
OPENAI_API_KEY=tu_clave_api
OPENWEATHER_API_KEY=tu_clave_clima
SQL_CONNECTION_STRING=tu_cadena_conexion_sql
```

## Uso

```bash
streamlit run Home.py
```

Luego carga los datos desde la página **"📂 Carga de Datos"** en el menú lateral.

## Estructura del Proyecto

- `Home.py`: Página principal y punto de entrada.
- `pages/`: Contiene los módulos individuales del dashboard.
- `data/`: Almacena los archivos de datos (Parquet, JSON, CSV).
- `utils/`: Funciones auxiliares y lógica compartida.
- `requirements.txt`: Lista de dependencias de Python.

## Contacto

Email: djinnxs@gmail.com
