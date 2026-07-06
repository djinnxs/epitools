import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io
from utils.common import query_duckdb, get_distinct_years
import duckdb

st.set_page_config(page_title="Epidemiologia", page_icon=":bar_chart:", layout="wide")

# Solo el título sin logo
st.markdown('<center><h3 style="font-weight:bold; padding:5px; border-radius:6px; width:100%;">🔎 Monitoreo de Notificación</h3></center>', unsafe_allow_html=True)

# Obtiene la semana actual
def get_epi_week(fecha):
    """Semana epidemiologica (semanas inician en domingo, SE1 contiene el 4 de enero)."""
    anio = fecha.year
    def inicio_se_1(year):
        cuatro_enero = date(year, 1, 4)
        retroceso = (cuatro_enero.weekday() + 1) % 7
        return cuatro_enero - timedelta(days=retroceso)
    inicio_actual = inicio_se_1(anio)
    if fecha < inicio_actual:
        inicio_anterior = inicio_se_1(anio - 1)
        return ((fecha - inicio_anterior).days // 7) + 1
    inicio_proximo = inicio_se_1(anio + 1)
    if fecha >= inicio_proximo:
        return 1
    return ((fecha - inicio_actual).days // 7) + 1

SemanActual = get_epi_week(date.today())

# Calcula la variable SemanaO
SemanaO = max(0, SemanActual - 2)


# Filtros Globales
col1, col2 = st.columns(2)
with col1:
    # Obtener años disponibles del parquet si es posible, sino lista fija o fallback
    # Usamos una query rápida a monitor_clinica.parquet
    try:
        years_df = query_duckdb("SELECT DISTINCT ANIO FROM {parquet} ORDER BY ANIO DESC", filename='monitor_clinica.parquet')
        years = years_df['ANIO'].tolist() if not years_df.empty else [2024, 2023, 2022]
    except:
        years = [2024, 2023, 2022]
        
    anio = st.selectbox("Año", years, index=0)

with col2:
    nivel = st.radio("Seleccione Nivel", ["Nacional", "Provincial"], horizontal=True, index=0)

# Cargar datos base filtrados por año
query_base = f"""
SELECT ORIGEN, CODIGO_DEPTO, DEPARTAMENTO, CODIGO_PROVINCIA, PROVINCIA, ANIO, SEMANA, ESTADO, FECHAREGISTROENCABEZADO, CANTIDAD
FROM {{parquet}}
WHERE ANIO = {anio}
"""
df = query_duckdb(query_base, filename='monitor_clinica.parquet')

if df.empty:
    st.warning(f"⚠️ No se encontraron datos para el año {anio}. Por favor ejecuta el ETL.")
    st.stop()

# --- LÓGICA NACIONAL ---
if nivel == "Nacional":
    pivot_table = df.pivot_table(
        values="CANTIDAD", index="ORIGEN", columns="SEMANA", aggfunc="first"
    ).fillna(0)
    pivot_table = pivot_table.reindex(columns=range(1, 53), fill_value=0)

    def style_cell(val):
        if val == 0:
            return "background-color: #0000FF"
        elif val > 0:
            return "background-color: #008000"
        else:
            return "background-color: #FF0000"

    styled_table = pivot_table.style.map(style_cell).format("{:.0f}")

    regularidad = df[df["SEMANA"] <= SemanaO].groupby("ORIGEN")["SEMANA"].nunique()
    ultima_semana_con_datos = df.groupby("ORIGEN")["SEMANA"].max()
    todos_origenes = ultima_semana_con_datos.index
    regularidad = regularidad.reindex(todos_origenes, fill_value=0)

    nueva_tabla = pd.DataFrame({
        "Establecimiento": todos_origenes,
        "Regularidad": regularidad.values,
        "Oportunidad": SemanaO - ultima_semana_con_datos.values
    })
    nueva_tabla.loc[nueva_tabla["Oportunidad"] < 0, "Oportunidad"] = 0
    nueva_tabla["Regularidad"] = (nueva_tabla["Regularidad"] * 100) / SemanaO

    cobertura = (nueva_tabla["Regularidad"] >= 50).sum() / len(nueva_tabla) if len(nueva_tabla) > 0 else 0
    notificacion_nula = (pivot_table == 0).sum().sum() / (pivot_table.shape[0] * pivot_table.shape[1]) if (pivot_table.shape[0] * pivot_table.shape[1]) > 0 else 0
    mediana_oportunidad = nueva_tabla["Oportunidad"].median() if not nueva_tabla["Oportunidad"].empty else 0
    mediana_regularidad = nueva_tabla["Regularidad"].median() if not nueva_tabla["Regularidad"].empty else 0

    def fmt(x):
        return f"{x:.1f}".replace(".", ",")

    titulo = f"Semana actual: {SemanActual} - Monitoreo Nacional - Regularidad: {fmt(mediana_regularidad)}% - Oportunidad: {fmt(mediana_oportunidad)} - Cobertura: {fmt(cobertura * 100)}% - Notificación nula: {fmt(notificacion_nula * 100)}%"
    st.markdown(f"<h3 style='text-align: center;'>{titulo}</h3>", unsafe_allow_html=True)

    st.write(styled_table.set_table_styles([
        {'selector': 'th', 'props': [('font-size', '14px'), ('width', '100px')]},
        {'selector': 'td', 'props': [('font-size', '14px'), ('width', '30px')]}
    ]).to_html(), unsafe_allow_html=True)

    excel_data = io.BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        pivot_table.to_excel(writer, sheet_name='Monitoreo', index=True)
    st.download_button("📥 Descargar Excel de Monitoreo", data=excel_data.getvalue(), file_name="Monitoreo_nacional.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("## Regularidad y Oportunidad de Notificación")
    st.write(nueva_tabla)
    excel_data2 = io.BytesIO()
    with pd.ExcelWriter(excel_data2, engine='xlsxwriter') as writer:
        nueva_tabla.to_excel(writer, sheet_name='Regularidad', index=False)
    st.download_button("📥 Descargar Excel de Regularidad", data=excel_data2.getvalue(), file_name="Regularidad_oportunidad_nacional.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- LÓGICA PROVINCIAL ---
else:
    provincias = sorted(df["PROVINCIA"].unique())
    provincia_seleccionada = st.selectbox("Provincia", provincias)

    deptos_prov = sorted(df[df["PROVINCIA"] == provincia_seleccionada]["DEPARTAMENTO"].unique().tolist())
    departamento_seleccionado = st.selectbox(
        "Departamento",
        ["Todos los departamentos"] + deptos_prov,
    )

    if departamento_seleccionado != "Todos los departamentos":
        df_filtered = df[(df["PROVINCIA"] == provincia_seleccionada) & (df["DEPARTAMENTO"] == departamento_seleccionado)]
    else:
        df_filtered = df[df["PROVINCIA"] == provincia_seleccionada]

    if df_filtered.empty:
        st.warning("No hay datos para la selección.")
        st.stop()

    pivot_table = df_filtered.pivot_table(
        values="CANTIDAD", index="ORIGEN", columns="SEMANA", aggfunc="first"
    ).fillna(0)
    pivot_table = pivot_table.reindex(columns=range(1, 53), fill_value=0)

    def style_cell(val):
        if val == 0:
            return "background-color: #0000FF"
        elif val > 0:
            return "background-color: #008000"
        else:
            return "background-color: #FF0000"

    styled_table = pivot_table.style.map(style_cell).format("{:.0f}")

    regularidad = df_filtered[df_filtered["SEMANA"] <= SemanaO].groupby("ORIGEN")["SEMANA"].nunique()
    ultima_semana_con_datos = df_filtered.groupby("ORIGEN")["SEMANA"].max()
    todos_origenes = ultima_semana_con_datos.index
    regularidad = regularidad.reindex(todos_origenes, fill_value=0)

    nueva_tabla = pd.DataFrame({
        "Establecimiento": todos_origenes,
        "Regularidad": regularidad.values,
        "Oportunidad": SemanaO - ultima_semana_con_datos.values
    })
    nueva_tabla.loc[nueva_tabla["Oportunidad"] < 0, "Oportunidad"] = 0
    nueva_tabla["Regularidad"] = (nueva_tabla["Regularidad"] * 100) / SemanaO

    cobertura = (nueva_tabla["Regularidad"] >= 50).sum() / len(nueva_tabla) if len(nueva_tabla) > 0 else 0
    notificacion_nula = (pivot_table == 0).sum().sum() / (pivot_table.shape[0] * pivot_table.shape[1]) if (pivot_table.shape[0] * pivot_table.shape[1]) > 0 else 0
    mediana_oportunidad = nueva_tabla["Oportunidad"].median() if not nueva_tabla["Oportunidad"].empty else 0
    mediana_regularidad = nueva_tabla["Regularidad"].median() if not nueva_tabla["Regularidad"].empty else 0

    def fmt(x):
        return f"{x:.1f}".replace(".", ",")

    titulo = f"Semana actual: {SemanActual} - Monitoreo {provincia_seleccionada}"
    if departamento_seleccionado != "Todos los departamentos":
        titulo += f" - {departamento_seleccionado}"
    titulo += f" - Regularidad: {fmt(mediana_regularidad)}% - Oportunidad: {fmt(mediana_oportunidad)} - Cobertura: {fmt(cobertura * 100)}% - Notificación nula: {fmt(notificacion_nula * 100)}%"
    st.markdown(f"<h3 style='text-align: center;'>{titulo}</h3>", unsafe_allow_html=True)

    st.write(styled_table.set_table_styles([
        {'selector': 'th', 'props': [('font-size', '14px'), ('width', '100px')]},
        {'selector': 'td', 'props': [('font-size', '14px'), ('width', '30px')]}
    ]).to_html(), unsafe_allow_html=True)

    excel_data = io.BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        pivot_table.to_excel(writer, sheet_name='Monitoreo', index=True)
    st.download_button("📥 Descargar Excel de Monitoreo", data=excel_data.getvalue(), file_name="Monitoreo.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("## Regularidad y Oportunidad de Notificación")
    st.write(nueva_tabla)
    excel_data2 = io.BytesIO()
    with pd.ExcelWriter(excel_data2, engine='xlsxwriter') as writer:
        nueva_tabla.to_excel(writer, sheet_name='Regularidad', index=False)
    st.download_button("📥 Descargar Excel de Regularidad", data=excel_data2.getvalue(), file_name="Regularidad_oportunidad.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")