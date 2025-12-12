import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts
import numpy as np
import datetime
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Epidemiologia", page_icon=":bar_chart:", layout="wide")

# Esto descarga la librería de iconos para que los iconos de área funcionen
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">', unsafe_allow_html=True)

# Reemplazamos el emoji &#x1F4C8; (línea) por el ícono vectorial de área
st.markdown('<center><h3 style="font-weight:bold; padding:5px; border-radius:6px; width:100%;"><i class="fa-solid fa-chart-area"></i> SNVS Corredores endémicos</h3></center>', unsafe_allow_html=True)
# Solo el título sin logo
#st.markdown('<center><h3 style="font-weight:bold; padding:5px; border-radius:6px; width:100%;">&#x1F4C8; SNVS Corredores endémicos</h3></center>', unsafe_allow_html=True)

from utils.common import query_duckdb, get_distinct_events, get_distinct_provinces, get_distinct_years

# Cargar filtros
events = get_distinct_events()
provinces = get_distinct_provinces()

# Sección de filtros
col1, col2 = st.columns(2)

with col1:
    filtro_evento = st.multiselect("Elije el Evento", events)

with col2:
    filtro_provincia = st.multiselect("Elije la Provincia", provinces)

col3, col4 = st.columns(2)

with col3:
    years = get_distinct_years()
    if not years:
        years = list(range(2024, 2018, -1))
    filtro_anio = st.selectbox("Selecciona el año", years)

with col4:
    filtro_semana = st.selectbox("Selecciona la semana", list(range(1, 52)))

# Botón para generar el gráfico
if st.button("Generar Gráfico"):
    # Construir query dinámica para DuckDB
    # DuckDB usa comillas simples para strings.
    # {parquet} será reemplazado por la ruta del archivo en query_duckdb
    
    where_clauses = [
        f"ANIO >= {filtro_anio - 5}",
        f"ANIO <= {filtro_anio}",
        "SEMANA != 53"
    ]
    
    if filtro_evento:
        # Formatear lista para SQL: 'Evento1', 'Evento2'
        eventos_str = ", ".join([f"'{e}'" for e in filtro_evento])
        where_clauses.append(f"NOMBREEVENTOAGRP IN ({eventos_str})")
        
    if filtro_provincia:
        prov_str = ", ".join([f"'{p}'" for p in filtro_provincia])
        where_clauses.append(f"PROVINCIA IN ({prov_str})")
        
    where_str = " AND ".join(where_clauses)
    
    query = f"""
    SELECT CODIGO_PROVINCIA, PROVINCIA, ANIO, SEMANA, ID_SNVS_EVENTO_AGRP,
           NOMBREEVENTOAGRP, IDEDAD, GRUPO, CANTIDAD, FECHAREGISTROCLINICA
    FROM {{parquet}}
    WHERE {where_str}
    """
        
    clinica = query_duckdb(query)
    
    if clinica.empty:
        st.warning("No hay datos para los filtros seleccionados.")
    else:
        # Procesamiento (igual que antes)
        # Ordenar las columnas alfabéticamente
        clinica.sort_values(['NOMBREEVENTOAGRP', 'PROVINCIA'], inplace=True)
        clinica.reset_index(drop=True, inplace=True)
        
        datos_filtrados = clinica.copy() # Ya está filtrado por SQL, pero mantenemos nombre variable
        
        # Generar cuartiles y crear matriz
        datos_filtrados.sort_values(by=['ANIO', 'SEMANA'], inplace=True)
        matriz = datos_filtrados.pivot_table(index='ANIO', columns='SEMANA', values='CANTIDAD', aggfunc='sum', fill_value=0)

        # Calcular los cuartiles para los 5 años anteriores al seleccionado
        anos_anteriores = matriz.index[
            (matriz.index >= filtro_anio - 5) & (matriz.index < filtro_anio)
        ]
        if not anos_anteriores.empty:
            cuartiles = matriz.loc[anos_anteriores].apply(lambda x: pd.Series(x).quantile([0.25, 0.5, 0.75])).T
            cuartiles.columns = ['Exito', 'Seguridad', 'Alerta']
            
            # Obtener los datos del año seleccionado
            if filtro_anio in matriz.index:
                matriz_anio = matriz.loc[filtro_anio].reset_index()
                datos_anio_actual = matriz.loc[filtro_anio].tolist()
            else:
                datos_anio_actual = [0] * 52 # O manejar como vacío

            # Crear la configuración del gráfico de ECharts
            options = {
                "title": {"text": f"Corredor de {', '.join(filtro_evento) if filtro_evento else 'Todos'}", "textStyle": {"fontSize": 20}},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
                "toolbox": {
                    "feature": {
                        "dataZoom": {"yAxisIndex": "none"},
                        "saveAsImage": {"type": "png"},
                        "magicType": {"type": ["line", "bar"]},
                    }
                },
                "dataZoom": [
                    {"type": "inside", "startValue": 0, "endValue": 52},
                    {"type": "slider", "startValue": 0, "endValue": 52},
                ],
                "legend": {"data": ["Exito", "Seguridad", "Alerta", f"Año {filtro_anio}"]},
                "grid": {"backgroundColor": "rgba(255, 0, 0, 0.1)"},
                "xAxis": {"type": "category", "data": list(range(1, 53))},
                "yAxis": {"type": "value"},
                "series": [
                    {
                        "name": "Exito",
                        "type": "line",
                        "stack": "Total",
                        "areaStyle": {"color": "rgba(144, 238, 144, 1)"},
                        "emphasis": {"focus": "series"},
                        "data": cuartiles['Exito'].tolist(),
                    },
                    {
                        "name": "Seguridad",
                        "type": "line",
                        "stack": "Total",
                        "areaStyle": {"color": "rgba(100, 149, 237, 1)"},
                        "emphasis": {"focus": "series"},
                        "data": cuartiles['Seguridad'].tolist(),
                    },
                    {
                        "name": "Alerta",
                        "type": "line",
                        "stack": "Total",
                        "areaStyle": {"color": "rgba(255, 255, 0, 1)"},
                        "emphasis": {"focus": "series"},
                        "data": cuartiles['Alerta'].tolist(),
                    },
                    {
                        "name": f"Año {filtro_anio}",
                        "type": "line",
                        "data": datos_anio_actual,
                        "lineStyle": {"color": "black", "width": 2},
                        "symbol": "circle",
                        "symbolSize": 4,
                        "itemStyle": {
                            "color": "white",
                            "borderColor": "red",
                            "borderWidth": 2
                        },
                    },
                ],
                "backgroundColor": "#ffffff",
            }

            # Cortar la línea negra en la semana seleccionada
            if len(options['series'][-1]['data']) >= filtro_semana:
                 options['series'][-1]['data'] = options['series'][-1]['data'][:filtro_semana] + [None] * (52 - filtro_semana)

            # Mostrar el gráfico de ECharts
            st_echarts(options=options, height="600px")
            
            # Sección para la fecha de última actualización
            if 'FECHAREGISTROCLINICA' in clinica.columns:
                last_update_date = clinica['FECHAREGISTROCLINICA'].max()
                st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)
                st.write(f"Última actualización: {last_update_date}")
        else:
             st.warning("No hay datos históricos suficientes para calcular el corredor (se necesitan 5 años previos).")

