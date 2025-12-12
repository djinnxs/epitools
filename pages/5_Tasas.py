import streamlit as st
import pandas as pd
import os
from utils.common import load_sql_data, download_excel, get_distinct_years, get_distinct_events, get_data_path

# Configuración de la página
st.set_page_config(page_title="Epidemiología", page_icon=":bar_chart:", layout="wide")

# Título
st.title(" 🏻 Tasas de Casos")

# Selector de Nivel
nivel = st.radio("Seleccione Nivel", ["Provincia", "Departamento"], horizontal=True)

# Filtros principales
col1, col2 = st.columns(2)
with col1:
    years = get_distinct_years()
    anio = st.selectbox("Año", years)
with col2:
    events = get_distinct_events()
    evento = st.selectbox("Evento", events)

# Selector adicional según nivel
provincia_sel = None
depto_sel = None

if nivel == 'Departamento':
    dept_parquet = get_data_path('proyecciones_depto_indec.parquet')
    df_pobl_depto = pd.read_parquet(dept_parquet)

    # Eliminar duplicados en los nombres de provincia
    provincias_disponibles = sorted(df_pobl_depto['juri_nombre'].str.title().unique())
    provincia_sel = st.selectbox('Selecciona la Provincia', provincias_disponibles)

    # Construir lista de departamentos
    deptos = []
    if provincia_sel and not df_pobl_depto.empty and 'departamento_nombre' in df_pobl_depto.columns:
        deptos = sorted(df_pobl_depto[df_pobl_depto['juri_nombre'].str.title() == provincia_sel]['departamento_nombre'].str.title().unique())
    if deptos:
        depto_sel = st.selectbox('Departamento', deptos)

# Botón Generar
if st.button('Generar Tabla'):
    st.session_state.generar_tasas = True
else:
    if 'generar_tasas' not in st.session_state:
        st.session_state.generar_tasas = False

if st.session_state.generar_tasas:
    @st.cache_data
    def load_population_data():
        prov_parquet = get_data_path('poblacionxprovinciaindec.parquet')
        dept_parquet = get_data_path('proyecciones_depto_indec.parquet')

        try:
            poblacion_prov = pd.read_parquet(prov_parquet)
            poblacion_depto = pd.read_parquet(dept_parquet)

            # Asegurar que 'juri' tenga siempre 5 dígitos para departamento
            poblacion_depto["juri"] = poblacion_depto["juri"].apply(lambda x: str(x).zfill(5))

            # Filtrar población por sexo "Ambos sexos" y agrupar
            poblacion_depto = poblacion_depto[poblacion_depto["sexo_nombre"] == "Ambos sexos"]
            poblacion_depto = poblacion_depto.groupby(["ano", "juri", "juri_nombre"], as_index=False)["poblacion"].sum()

            # Asegurar que no haya duplicados en la población por provincia
            poblacion_prov = poblacion_prov[poblacion_prov["sexo_nombre"] == "Ambos sexos"]
            poblacion_prov = poblacion_prov.groupby(["ano", "juri", "juri_nombre"], as_index=False)["poblacion"].sum()

            return poblacion_prov, poblacion_depto
        except Exception as e:
            st.error(f"Error cargando población desde Parquet: {e}")
            st.stop()

    poblacion_prov, poblacion_depto = load_population_data()

    # Cargar datos filtrados
    query = """
    SELECT [CODIGO_PROVINCIA], [PROVINCIA], [DEPARTAMENTO], [COD_DEPTO], [ANIO], [NOMBREEVENTOAGRP], [CANTIDAD]
    FROM [SNVS2].[dbo].[DashClinica2]
    WHERE ANIO = ? AND NOMBREEVENTOAGRP = ?
    """
    filtered = load_sql_data(query, params=(anio, evento))
    if filtered.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        st.stop()

    # Agrupar datos
    df_agrupado = filtered.groupby(['PROVINCIA', 'DEPARTAMENTO', 'ANIO', 'NOMBREEVENTOAGRP'], as_index=False).agg({
        'CODIGO_PROVINCIA': 'first',
        'COD_DEPTO': 'first',
        'CANTIDAD': 'sum'
    })

    # Asegurar que los códigos de provincia y departamento tengan el formato correcto
    df_agrupado['CODIGO_PROVINCIA'] = df_agrupado['CODIGO_PROVINCIA'].apply(lambda x: f"{int(x):02d}")
    df_agrupado['COD_DEPTO'] = df_agrupado['COD_DEPTO'].apply(lambda x: str(x).zfill(5))

    if nivel == 'Provincia':
        st.subheader("Tasas por Provincia")
        agrupado_prov = df_agrupado.groupby(["PROVINCIA", "CODIGO_PROVINCIA"], as_index=False)["CANTIDAD"].sum()

        # Filtrar población por año y sexo "Ambos sexos"
        poblacion_prov_filtrada = poblacion_prov[poblacion_prov["ano"] == anio]

        # Asegurar que 'juri' y 'CODIGO_PROVINCIA' sean strings y tengan el formato correcto
        poblacion_prov_filtrada['juri'] = poblacion_prov_filtrada['juri'].astype(str).apply(lambda x: f"{int(x):02d}")
        agrupado_prov['CODIGO_PROVINCIA'] = agrupado_prov['CODIGO_PROVINCIA'].astype(str)

        # Unir con los datos de población
        merged = pd.merge(agrupado_prov, poblacion_prov_filtrada, left_on='CODIGO_PROVINCIA', right_on='juri', how='left')

        # Calcular tasa
        merged['Tasas'] = (merged['CANTIDAD'] / merged['poblacion']) * 100000
        merged['Tasas'] = merged['Tasas'].round(2)
        merged['PROVINCIA'] = merged['PROVINCIA'].str.title()

        # Formatear números
        merged['Población'] = merged['poblacion']
        merged['Tasas'] = merged['Tasas'].apply(lambda x: f"{x:,.2f}".replace('.', 'temp').replace(',', '.').replace('temp', ','))
        merged['Cantidad'] = merged['CANTIDAD'].apply(lambda x: f"{x:,}".replace(',', 'temp').replace('.', ',').replace('temp', '.'))

        # Seleccionar y renombrar columnas
        result = merged[['PROVINCIA', 'Cantidad', 'Población', 'Tasas']].sort_values('Tasas', ascending=False)

        st.write(result)

        # Descargar Excel
        excel_data, excel_name = download_excel(result, "tasas_provincia.xlsx")
        st.download_button("Descargar Excel Provincia", excel_data, excel_name)

    else:
        st.subheader("Tasas por Departamento")
        agrupado_depto = df_agrupado[df_agrupado['PROVINCIA'].str.title() == provincia_sel]
        agrupado_depto = agrupado_depto.groupby(["DEPARTAMENTO", "COD_DEPTO"], as_index=False)["CANTIDAD"].sum()

        # Filtrar población por año y sexo "Ambos sexos"
        poblacion_depto_filtrada = poblacion_depto[poblacion_depto["ano"] == anio]

        # Asegurar que 'juri' y 'COD_DEPTO' sean strings y tengan el formato correcto
        poblacion_depto_filtrada['juri'] = poblacion_depto_filtrada['juri'].astype(str)
        agrupado_depto['COD_DEPTO'] = agrupado_depto['COD_DEPTO'].astype(str)

        # Unir con los datos de población
        merged = pd.merge(agrupado_depto, poblacion_depto_filtrada, left_on='COD_DEPTO', right_on='juri', how='left')

        # Calcular tasa
        merged['Tasas'] = (merged['CANTIDAD'] / merged['poblacion']) * 100000
        merged['Tasas'] = merged['Tasas'].round(2)
        merged['DEPARTAMENTO'] = merged['DEPARTAMENTO'].str.title()
        merged = merged.sort_values(['DEPARTAMENTO'])

        # Formatear números
        merged['Población'] = merged['poblacion']
        merged['Tasas'] = merged['Tasas'].apply(lambda x: f"{x:,.2f}".replace('.', 'temp').replace(',', '.').replace('temp', ','))
        merged['Cantidad'] = merged['CANTIDAD'].apply(lambda x: f"{x:,}".replace(',', 'temp').replace('.', ',').replace('temp', '.'))

        # Seleccionar y renombrar columnas
        result = merged[['DEPARTAMENTO', 'Cantidad', 'Población', 'Tasas']]

        st.write(result)

        # Descargar Excel
        excel_data, excel_name = download_excel(result, "tasas_departamento.xlsx")
        st.download_button("Descargar Excel Departamento", excel_data, excel_name)
