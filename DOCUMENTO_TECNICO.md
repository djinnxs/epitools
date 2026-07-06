# SEI - Sistema de Epidemiología Interactiva
## Documento Técnico Arquitectónico y Funcional

Este documento está dirigido a tomadores de decisión, responsables de IT, consultores técnicos y compradores potenciales. Su objetivo es brindar una visión integral de la arquitectura, las capacidades tecnológicas y el valor agregado del Sistema de Epidemiología Interactiva (SEI).

---

### 1. Resumen Ejecutivo
El **SEI (Sistema de Epidemiología Interactiva)** es una solución analítica avanzada desarrollada en Python bajo el framework de **Streamlit**. Está diseñada para el procesamiento masivo, visualización interactiva y análisis predictivo de datos epidemiológicos y geoespaciales a nivel nacional (Argentina). 
La plataforma no solo digitaliza la vigilancia epidemiológica, sino que incorpora módulos de Inteligencia Artificial, análisis climático y procesamiento en tiempo real.

### 2. Arquitectura de Software y Stack Tecnológico
La aplicación sigue un modelo de arquitectura orientada a la explotación ágil de datos y despliegue rápido (Data Apps).

*   **Frontend y Orquestación:** `Streamlit` (Python). Permite el renderizado web dinámico y reactivo a los inputs del usuario sin latencia excesiva.
*   **Procesamiento de Datos (ETL & Core):** 
    *   `Pandas` y `NumPy` para manipulación de dataframes.
    *   `DuckDB` y formato `Parquet` para almacenamiento columnar y consultas analíticas ultrarrápidas, optimizando el consumo de RAM.
*   **Visualización y GIS (Sistemas de Información Geográfica):**
    *   `Plotly` y `Altair` para gráficos interactivos.
    *   `Folium` para el renderizado de mapas dinámicos y geolocalización.
*   **Inteligencia Artificial y Modelado Predictivo:**
    *   Modelos estadísticos avanzados (`statsmodels`) para algoritmos de Nowcasting y series temporales (SARIMA).
    *   Integración con APIs de modelos de lenguaje grande (LLMs) para el módulo de "Asistente IA", permitiendo consultas en lenguaje natural (NLP).
*   **Entorno y Despliegue:** Soporte nativo para despliegue On-Premise, en la Nube (AWS, Azure, GCP) mediante contenedores Docker, o a través de Streamlit Community Cloud.

---

### 3. Descripción Técnica de Módulos (Hojas)

La aplicación está modularizada en múltiples scripts de renderizado (`pages/`) que se comunican con un núcleo central de datos en memoria.

#### A. Módulo Core y Dashboard (`1_Dashboard`, `3_CasosSemana`, `10_Monitoreo`, `14_Tendencia`)
Actúan como el punto de entrada principal. Consumen los datos agregados y procesados de Parquet, ejecutando filtros en tiempo real sobre la base de datos completa. Generan KPIs de rendimiento epidemiológico.

#### B. Módulo Geoespacial (`4_Mapas`, `19_MapaAnimado`, `22_Semaforo`)
Integran capas vectoriales (GeoJSON/Shapefiles) y datos tabulares. El *Mapa Animado* renderiza secuencias temporales para observar dinámicas de dispersión geográfica. El *Semáforo* automatiza la estratificación de riesgo utilizando reglas de negocio configurables.

#### C. Módulo de Epidemiología Analítica y Exploración Avanzada (`2_Corredores`, `5_Tasas`, `6_Tablas`, `7_Poblacion`, `9_Mediana`, `15_Avanzado`)
Digitaliza metodologías epidemiológicas estandarizadas internacionalmente. El algoritmo de *Corredores Endémicos* calcula las bandas de expectativa (cuartiles o desviación estándar) basadas en datos históricos de 5 a 7 años, ajustando automáticamente años pandémicos. Los submódulos avanzados (`Avanzado` y `Tablas`) integran el motor de exploración PyGWalker para Business Intelligence dinámico y herramientas de comparación temporal, etaria y correlación cruzada de eventos.

#### D. Módulo Climático y Ambiental (`12_Clima`, `20_CorrelacionClima`, `21_Sindemias`)
Representa una de las ventajas competitivas de SEI. Cruza grandes volúmenes de datos meteorológicos (APIs o series históricas) con las curvas de contagio, aplicando tests de correlación estadística (Pearson/Spearman) para demostrar causalidad ambiental (ej. Vector-Clima).

#### E. Módulo de Inteligencia y Predicción (`13_IA`, `17_Nowcasting`, `18_Alertas`, `11_Rumores`)
*   **Nowcasting:** Estima infecciones presentes no reportadas basándose en el patrón histórico de retraso en la notificación de los centros de salud.
*   **Asistente IA:** Un pipeline que traduce la consulta del usuario a código de consulta de datos, ejecuta la extracción y devuelve una interpretación narrativa del resultado.
*   **Alertas:** Motor de reglas que se ejecuta sobre los nuevos lotes de datos y lanza notificaciones ante anomalías estadísticas.

---

### 4. Ventajas Competitivas para la Organización

1.  **Alto Desempeño y Escalabilidad:** El uso de archivos `.parquet` en lugar de consultas pesadas a bases de datos transaccionales, reduce los tiempos de carga en un 90% y minimiza costos de infraestructura.
2.  **Soberanía de Datos:** La arquitectura permite que todo el procesamiento se realice `On-Premise` si las regulaciones de protección de datos médicos locales (como HIPAA o equivalentes) lo exigen.
3.  **Innovación Sanitaria:** La inclusión de *Nowcasting* e *Inteligencia Artificial* posiciona a la institución compradora en la vanguardia de la tecnología gubernamental o de salud privada (HealthTech).
4.  **Bajo Costo de Mantenimiento:** Al ser un desarrollo íntegramente en Python, no requiere licenciamientos de software privativo caros (como Tableau o PowerBI) y es fácilmente mantenible por científicos de datos estándar.

### 5. Requisitos Recomendados de Infraestructura

Para un entorno de producción (despliegue web):
*   **Servidor:** Linux (Ubuntu 20.04+ / Debian) o contenedor Docker.
*   **CPU:** 4 vCPUs (Mínimo) - 8 vCPUs (Recomendado).
*   **RAM:** 8 GB (Mínimo) - 16 GB+ (Recomendado, dependiendo del volumen de datos históricos).
*   **Almacenamiento:** 50 GB SSD.
*   **Conectividad:** Acceso de salida para APIs climáticas y LLM (si aplica). Acceso HTTP/HTTPS para usuarios finales.

---
*Este documento es una descripción de arquitectura técnica sujeta a personalizaciones según el acuerdo de implementación (SLA).*
