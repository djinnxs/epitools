# pages/6_Tablas.py
import streamlit as st
from utils.common import query_duckdb
from pygwalker.api.streamlit import StreamlitRenderer
import os

st.set_page_config(page_title="Epidemiologia", page_icon=":bar_chart:", layout="wide")
# Título
st.title('📚 Opción tableau')
st.subheader('Alternativa estilo tableau para análisis de datos')

# DuckDB query
query = """
SELECT PROVINCIA, DEPARTAMENTO, ANIO, SEMANA, NOMBREEVENTOAGRP, GRUPO, CANTIDAD
FROM {parquet}
"""
df = query_duckdb(query)

if not df.empty:
    renderer = StreamlitRenderer(df, spec=os.path.join(os.path.dirname(__file__), '..', 'gw_config.json'))
    renderer.explorer()
else:
    st.warning("No hay datos disponibles.")