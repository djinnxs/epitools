import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.common import query_duckdb
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Análisis Avanzado", page_icon=":chart_with_upwards_trend:", layout="wide")
st.title("📊 Análisis Avanzado")

# DuckDB query
query = """
SELECT PROVINCIA, DEPARTAMENTO, ANIO, SEMANA, NOMBREEVENTOAGRP, GRUPO, CANTIDAD
FROM {parquet}
"""
df = query_duckdb(query)

if df.empty:
    st.error("No hay datos disponibles")
    st.stop()

# Selector de tipo de análisis
analisis_tipo = st.selectbox(
    "Selecciona el tipo de análisis",
    ["Tendencia Temporal", "Correlación por Evento", "Distribución por Grupo Etario", "Comparativa de Provincias"]
)

# 1. TENDENCIA TEMPORAL
if analisis_tipo == "Tendencia Temporal":
    st.subheader("Tendencia de Casos por Evento")
    
    eventos = sorted(df["NOMBREEVENTOAGRP"].unique())
    evento_seleccionado = st.selectbox("Selecciona un evento", eventos)
    
    df_evento = df[df["NOMBREEVENTOAGRP"] == evento_seleccionado]
    df_temporal = df_evento.groupby(["ANIO", "SEMANA"])["CANTIDAD"].sum().reset_index()
    df_temporal["fecha"] = df_temporal["ANIO"].astype(str) + "-W" + df_temporal["SEMANA"].astype(str).str.zfill(2)
    
    fig = px.line(
        df_temporal,
        x="fecha",
        y="CANTIDAD",
        title=f"Tendencia de {evento_seleccionado}",
        labels={"CANTIDAD": "Casos", "fecha": "Año-Semana"},
        markers=True
    )
    fig.update_layout(hovermode="x unified", height=500)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de datos
    st.dataframe(df_temporal[["ANIO", "SEMANA", "CANTIDAD"]], use_container_width=True)

# 2. CORRELACIÓN POR EVENTO
elif analisis_tipo == "Correlación por Evento":
    st.subheader("Comparación de Eventos por Año")
    
    anio_seleccionado = st.selectbox("Selecciona un año", sorted(df["ANIO"].unique(), reverse=True))
    
    df_anio = df[df["ANIO"] == anio_seleccionado]
    df_eventos = df_anio.groupby("NOMBREEVENTOAGRP")["CANTIDAD"].sum().reset_index()
    df_eventos = df_eventos.sort_values("CANTIDAD", ascending=False)
    
    fig = px.bar(
        df_eventos,
        x="NOMBREEVENTOAGRP",
        y="CANTIDAD",
        title=f"Casos por Evento en {anio_seleccionado}",
        labels={"CANTIDAD": "Casos", "NOMBREEVENTOAGRP": "Evento"},
        color="CANTIDAD",
        color_continuous_scale="Blues"
    )
    fig.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(df_eventos, use_container_width=True)

# 3. DISTRIBUCIÓN POR GRUPO ETARIO
elif analisis_tipo == "Distribución por Grupo Etario":
    st.subheader("Distribución por Grupo Etario")
    
    eventos = sorted(df["NOMBREEVENTOAGRP"].unique())
    evento_seleccionado = st.selectbox("Selecciona un evento", eventos)
    
    df_evento = df[df["NOMBREEVENTOAGRP"] == evento_seleccionado]
    df_grupos = df_evento.groupby("GRUPO")["CANTIDAD"].sum().reset_index()
    df_grupos = df_grupos.dropna(subset=["GRUPO"])
    df_grupos = df_grupos.sort_values("CANTIDAD", ascending=False)
    
    fig = px.pie(
        df_grupos,
        names="GRUPO",
        values="CANTIDAD",
        title=f"Distribución de {evento_seleccionado} por Grupo Etario"
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(df_grupos, use_container_width=True)

# 4. COMPARATIVA DE PROVINCIAS
elif analisis_tipo == "Comparativa de Provincias":
    st.subheader("Comparación de Provincias")
    
    evento_seleccionado = st.selectbox("Selecciona un evento", sorted(df["NOMBREEVENTOAGRP"].unique()))
    anio_seleccionado = st.selectbox("Selecciona un año", sorted(df["ANIO"].unique(), reverse=True))
    
    df_filtrado = df[(df["NOMBREEVENTOAGRP"] == evento_seleccionado) & (df["ANIO"] == anio_seleccionado)]
    df_provincias = df_filtrado.groupby("PROVINCIA")["CANTIDAD"].sum().reset_index()
    df_provincias = df_provincias.sort_values("CANTIDAD", ascending=False)
    
    fig = px.bar(
        df_provincias,
        x="PROVINCIA",
        y="CANTIDAD",
        title=f"{evento_seleccionado} por Provincia ({anio_seleccionado})",
        labels={"CANTIDAD": "Casos", "PROVINCIA": "Provincia"},
        color="CANTIDAD",
        color_continuous_scale="Reds"
    )
    fig.update_layout(height=500, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(df_provincias, use_container_width=True)