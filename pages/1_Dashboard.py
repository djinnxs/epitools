# pages/1_Dashboard.py
import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.figure_factory as ff
from collections import OrderedDict
import duckdb
from utils.common import get_parquet_path, check_parquet_exists

# Configuración
st.set_page_config(page_title="Epidemiologia", page_icon="Chart", layout="wide")

# ==================== CARGA DE DATOS DESDE PARQUET (SIN LOCALIDAD) ====================
@st.cache_data(ttl=3600)
def load_data():
    parquet_path = check_parquet_exists('base_semanal.parquet')
    if not parquet_path:
        st.error("No se encontró base_semanal.parquet")
        st.stop()

    clean_path = str(parquet_path).replace("\\", "/")
    
    df = duckdb.query(f"""
        SELECT 
            CODIGO_PROVINCIA, PROVINCIA, DEPARTAMENTO,
            ANIO, SEMANA, ID_SNVS_EVENTO_AGRP, NOMBREEVENTOAGRP,
            IDEDAD, GRUPO, CANTIDAD, FECHAREGISTROCLINICA
        FROM read_parquet('{clean_path}')
    """).df()
    
    df["FECHAREGISTROCLINICA"] = pd.to_datetime(df["FECHAREGISTROCLINICA"], errors='coerce')
    df["NOMBREEVENTOAGRP"] = df["NOMBREEVENTOAGRP"].astype(str)
    return df

# CARGAMOS PRIMERO
df = load_data()

# Muestra rápida
if st.checkbox("Usar datos de muestra (para desarrollo rápido)"):
    df = df.sample(n=1000, random_state=42).reset_index(drop=True)

# ==================== RANGO DE FECHAS (CORREGIDO) ====================
startDate = df["FECHAREGISTROCLINICA"].min().date()
endDate = df["FECHAREGISTROCLINICA"].max().date()

col1, col2 = st.columns(2)
with col1:
    date1 = st.date_input("Fecha inicial", startDate)
    date1 = pd.Timestamp(date1)  # ← CONVERTIMOS A TIMESTAMP
with col2:
    date2 = st.date_input("Fecha final", endDate)
    date2 = pd.Timestamp(date2)  # ← CONVERTIMOS A TIMESTAMP

# ==================== FILTROS ====================
st.sidebar.header("Elije el filtro:")

ANIO = st.sidebar.multiselect("Elije el año", sorted(df["ANIO"].dropna().unique()))

col_evento, col_provincia, col_grupo = st.columns(3)
with col_evento:
    EVENTO = st.multiselect("Evento", ["Todos"] + sorted(df["NOMBREEVENTOAGRP"].unique()), default=["Todos"])
with col_provincia:
    PROVINCIA = st.multiselect("Provincia", ["Todas"] + sorted(df["PROVINCIA"].unique()), default=["Todas"])
with col_grupo:
    GRUPO_ORDER = [
        "< 6 m","6 a 11 m","12 a 23 m","2 a 4","5 a 9","10 a 14",
        "15 a 19","20 a 24","25 a 34","35 a 44","45 a 64",
        "65 a 74",">= a 75","Pediát <3","Pediát >=3",
        "Adultos <60","Adultos >=60","Edad Sin Esp."
    ]
    available = list(df["GRUPO"].dropna().unique())
    ordered = [g for g in GRUPO_ORDER if g in available]
    remaining = sorted([g for g in available if g not in ordered])
    GRUPO = st.multiselect("Grupo Etario", ["Todos"] + ordered + remaining, default=["Todos"])

DEPARTAMENTO = st.sidebar.multiselect("Elije el departamento", ["Todos"] + sorted(df["DEPARTAMENTO"].dropna().unique()))

# ==================== FILTRADO (CORREGIDO) ====================
@st.cache_data
def filter_dataframe(df, date1, date2, ANIO, EVENTO, PROVINCIA, GRUPO, DEPARTAMENTO):
    f = df[(df["FECHAREGISTROCLINICA"] >= date1) & 
           (df["FECHAREGISTROCLINICA"] <= date2)].copy()
    
    if ANIO: 
        f = f[f["ANIO"].isin(ANIO)]
    if EVENTO and EVENTO != ["Todos"]: 
        f = f[f["NOMBREEVENTOAGRP"].isin(EVENTO)]
    if PROVINCIA and PROVINCIA != ["Todas"]: 
        f = f[f["PROVINCIA"].isin(PROVINCIA)]
    if GRUPO and GRUPO != ["Todos"]: 
        f = f[f["GRUPO"].isin(GRUPO)]
    if DEPARTAMENTO and DEPARTAMENTO != ["Todos"]: 
        f = f[f["DEPARTAMENTO"].isin(DEPARTAMENTO)]
    
    return f

filtered_df = filter_dataframe(df, date1, date2, ANIO, EVENTO, PROVINCIA, GRUPO, DEPARTAMENTO)

# ==================== RESTO DEL DASHBOARD (100% IGUAL QUE ANTES) ===

# Gráfico por provincia
PROVINCIA_df = filtered_df.groupby("PROVINCIA", as_index=False)["CANTIDAD"].sum()

@st.cache_data
def create_provincia_chart(df):
    fig = px.bar(df, x="PROVINCIA", y="CANTIDAD",
                 text=[f'{x:,.0f}' for x in df["CANTIDAD"]],
                 template="seaborn")
    fig.update_traces(textposition="outside")
    fig.update_layout(xaxis_tickangle=45)
    return fig

col1, col2 = st.columns(2)
with col1:
    st.subheader("Cantidad por provincia")
    st.plotly_chart(create_provincia_chart(PROVINCIA_df), use_container_width=True)

# Donut por evento
@st.cache_data
def create_pie_chart(df):
    fig = px.pie(df, values="CANTIDAD", names="NOMBREEVENTOAGRP", hole=0.5)
    fig.update_traces(textposition="outside", textinfo='percent+label')
    return fig

with col2:
    st.subheader("Cantidad por evento")
    if not filtered_df.empty:
        st.plotly_chart(create_pie_chart(filtered_df), use_container_width=True)

# Descargas
cl1, cl2 = st.columns(2)
with cl1:
    with st.expander("Ver datos de provincia"):
        st.write(PROVINCIA_df.style.background_gradient(cmap="Blues"))
        st.download_button("Descargar datos", PROVINCIA_df.to_csv(index=False).encode('utf-8'), "PROVINCIA.csv", "text/csv")
with cl2:
    with st.expander("Ver datos de eventos"):
        eventos_df = filtered_df.groupby("NOMBREEVENTOAGRP", as_index=False)["CANTIDAD"].sum()
        st.write(eventos_df.style.background_gradient(cmap="Oranges"))
        st.download_button("Descargar datos", eventos_df.to_csv(index=False).encode('utf-8'), "Eventos.csv", "text/csv")

# Serie de tiempo
@st.cache_data
def create_time_series(df):
    df_copy = df.copy()
    df_copy["mes_año"] = df_copy["FECHAREGISTROCLINICA"].dt.to_period("M")
    linechart = pd.DataFrame(df_copy.groupby(df_copy["mes_año"].dt.strftime("%Y : %b"))["CANTIDAD"].sum()).reset_index()
    fig = px.line(linechart, x="mes_año", y="CANTIDAD", labels={"CANTIDAD": "Cantidad"}, height=500, template="gridon")
    return fig, linechart

st.subheader('Análisis serie de tiempo')
if not filtered_df.empty:
    fig2, linechart = create_time_series(filtered_df)
    st.plotly_chart(fig2, use_container_width=True)
    with st.expander("Datos Serie de tiempo:"):
        st.write(linechart.T.style.background_gradient(cmap="Blues"))
        st.download_button('Descargar datos', linechart.to_csv(index=False).encode("utf-8"), "SerieTiempo.csv", "text/csv")

# Treemap (sin LOCALIDAD)
@st.cache_data
def create_treemap(df):
    fig = px.treemap(df, path=["PROVINCIA", "DEPARTAMENTO"],
                     values="CANTIDAD", hover_data=["CANTIDAD"], color="DEPARTAMENTO")
    fig.update_layout(width=800, height=650)
    return fig

st.subheader("Vista jerárquica en mapa árbol")
if not filtered_df.empty:
    st.plotly_chart(create_treemap(filtered_df), use_container_width=True)

# Tabla de ejemplo (sin LOCALIDAD)
st.subheader("Resumen de eventos por mes y por provincia")
with st.expander("Resumen de tabla"):
    if not filtered_df.empty:
        sample = filtered_df.head(5)[["PROVINCIA", "DEPARTAMENTO", "NOMBREEVENTOAGRP", "GRUPO", "ANIO", "SEMANA", "CANTIDAD"]]
        fig = ff.create_table(sample, colorscale="Spectral")
        st.plotly_chart(fig, use_container_width=True)

# Tabla pivot mensual
meses_espanol = OrderedDict({1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'})
meses_orden = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

@st.cache_data
def create_pivot_table(df):
    df_copy = df.copy()
    df_copy["month_num"] = df_copy["FECHAREGISTROCLINICA"].dt.month
    df_copy["month"] = df_copy["month_num"].map(meses_espanol)
    pivot = pd.pivot_table(df_copy, values="CANTIDAD", index="NOMBREEVENTOAGRP",
                           columns="month", fill_value=0, aggfunc="sum")
    pivot = pivot[[col for col in meses_orden if col in pivot.columns]]
    return pivot

st.markdown("### Tabla por evento y mes")
if not filtered_df.empty:
    pivot = create_pivot_table(filtered_df)
    st.write(pivot.style.background_gradient(cmap="Blues", axis=1))
    st.download_button("Descargar tabla mensual", pivot.to_csv().encode('utf-8'), "tabla_mensual.csv", "text/csv")
else:
    st.info("No hay datos")

st.markdown("---")
st.caption(f"Total de registros filtrados: **{len(filtered_df):,}** casos")
