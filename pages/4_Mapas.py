import streamlit as st
import plotly.express as px
import geopandas as gpd
import pandas as pd
import os
from utils.common import load_sql_data, style_table, download_excel, get_distinct_years, get_distinct_events, get_data_path

st.set_page_config(page_title="Epidemiologia", page_icon=":bar_chart:", layout="wide")
st.title("🌎 Mapas de Casos y Tasas")

# Función para cargar GeoJSON con simplificación para mejorar rendimiento
@st.cache_data
def load_geojson_files():
    geojson_prov = get_data_path('provincia.json')
    geojson_depto = get_data_path('departamento.json')

    try:
        gdf_prov = gpd.read_file(geojson_prov)
        gdf_prov['geometry'] = gdf_prov['geometry'].simplify(tolerance=0.01, preserve_topology=True)

        if os.path.exists(geojson_depto):
            gdf_depto = gpd.read_file(geojson_depto)
            gdf_depto['geometry'] = gdf_depto['geometry'].simplify(tolerance=0.01, preserve_topology=True)
        else:
            st.error("Archivo departamento.json no encontrado.")
            st.stop()
        return gdf_prov, gdf_depto
    except Exception as e:
        st.error(f"Error cargando GeoJSON: {e}")
        st.stop()

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

# Mostrar spinner mientras carga
with st.spinner('Cargando datos geográficos...'):
    gdf_prov, gdf_depto = load_geojson_files()
    poblacion_prov, poblacion_depto = load_population_data()

# Filtros
col1, col2, col3 = st.columns(3)
with col1:
    years = get_distinct_years()
    anio = st.selectbox("Año", years)
with col2:
    events = get_distinct_events()
    evento = st.selectbox("Evento", events)
with col3:
    metrica = st.selectbox("Métrica", ["Casos", "Tasa x100k"])

# Botón Generar Mapa
if st.button("Generar Mapas", key="gen_map_btn"):
    st.session_state.generate_map = True
else:
    if "generate_map" not in st.session_state:
        st.session_state.generate_map = False

if not st.session_state.generate_map:
    st.info("Selecciona los filtros y haz clic en 'Generar Mapas' para visualizar.")
    st.stop()

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

# Agrupar datos como en tu proyecto anterior
df_agrupado = filtered.groupby(['PROVINCIA', 'DEPARTAMENTO', 'ANIO', 'NOMBREEVENTOAGRP'], as_index=False).agg({
    'CODIGO_PROVINCIA': 'first',
    'COD_DEPTO': 'first',
    'CANTIDAD': 'sum'
})

# Asegurar que los códigos de provincia y departamento tengan el formato correcto
df_agrupado['CODIGO_PROVINCIA'] = df_agrupado['CODIGO_PROVINCIA'].apply(lambda x: f"{int(x):02d}")
df_agrupado['COD_DEPTO'] = df_agrupado['COD_DEPTO'].apply(lambda x: str(x).zfill(5))

# Layout: Dos columnas para los mapas
left_col, right_col = st.columns(2)

# --- MAPA PROVINCIA (Izquierda) ---
with left_col:
    st.subheader("Nivel Provincia")
    agrupado_prov = df_agrupado.groupby(["PROVINCIA", "CODIGO_PROVINCIA"], as_index=False)["CANTIDAD"].sum()

    # Unir con el GeoJSON de provincias
    merge_prov = gdf_prov.merge(agrupado_prov, left_on='in1', right_on='CODIGO_PROVINCIA', how='left')
    merge_prov["CANTIDAD"] = merge_prov["CANTIDAD"].fillna(0)

    if metrica == "Tasa x100k":
        # Filtrar población por año y sexo "Ambos sexos"
        poblacion_prov_filtrada = poblacion_prov[poblacion_prov["ano"] == anio]

        # Asegurar que 'juri' y 'CODIGO_PROVINCIA' sean strings y tengan el formato correcto
        poblacion_prov_filtrada['juri'] = poblacion_prov_filtrada['juri'].astype(str).apply(lambda x: f"{int(x):02d}")
        merge_prov['CODIGO_PROVINCIA'] = merge_prov['CODIGO_PROVINCIA'].astype(str)

        # Unir con los datos de población
        merge_prov = merge_prov.merge(
            poblacion_prov_filtrada,
            left_on='CODIGO_PROVINCIA',
            right_on='juri',
            how='left'
        )

        # Calcular tasa
        merge_prov["TASA"] = (merge_prov["CANTIDAD"] / merge_prov["poblacion"]) * 100000
        merge_prov["TASA"] = merge_prov["TASA"].round(2)  # Redondear a 2 decimales
        color_col_prov = "TASA"
        title_prov = f"Tasa x100k - {evento} (Provincia)"
    else:
        color_col_prov = "CANTIDAD"
        title_prov = f"Casos - {evento} (Provincia)"

    fig_prov = px.choropleth_mapbox(
        merge_prov,
        geojson=merge_prov.geometry.__geo_interface__,
        locations=merge_prov.index,
        color=color_col_prov,
        hover_name="nam",
        hover_data={color_col_prov: ':.2f', "poblacion": True, "CANTIDAD": True} if metrica == "Tasa x100k" else {color_col_prov: True, "CANTIDAD": True},
        mapbox_style="carto-positron",
        center={"lat": -40.0, "lon": -60.0},
        zoom=3,
        color_continuous_scale="Reds" if metrica == "Casos" else "Blues"
    )
    fig_prov.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        title_text=title_prov,
        title_x=0.5
    )
    st.plotly_chart(fig_prov, use_container_width=True, config={'displayModeBar': False})

    # Tabla Provincia
    if not merge_prov.empty:
        tabla_prov = merge_prov[["nam", "CANTIDAD", "poblacion", color_col_prov]].copy()
        tabla_prov.rename(columns={"nam": "Provincia", "CANTIDAD": "Casos", "poblacion": "Población", color_col_prov: "Tasas"}, inplace=True)
        tabla_prov["Provincia"] = tabla_prov["Provincia"].str.title()  # Formatear nombre de provincia
        tabla_prov = tabla_prov.dropna(subset=["Casos", "Población"])
        tabla_prov = tabla_prov.drop_duplicates()  # Eliminar filas duplicadas
        if not tabla_prov.empty:
            st.write("Datos por Provincia")
            tabla_prov_sorted = tabla_prov.sort_values("Tasas", ascending=False)  # Ordenar por Tasas
            st.dataframe(tabla_prov_sorted[["Provincia", "Casos", "Población", "Tasas"]], use_container_width=True)
            excel_prov, name_prov = download_excel(tabla_prov_sorted, "mapa_provincia.xlsx")
            st.download_button("Descargar Excel Provincia", excel_prov, name_prov)

# --- MAPA DEPARTAMENTO (Derecha) ---
with right_col:
    st.subheader("Nivel Departamento")
    agrupado_depto = df_agrupado.groupby(["DEPARTAMENTO", "COD_DEPTO", "PROVINCIA"], as_index=False)["CANTIDAD"].sum()

    # Unir con el GeoJSON
    merge_depto = gdf_depto.merge(agrupado_depto, left_on='in1', right_on='COD_DEPTO', how='inner')

    # Filtrar población por año
    poblacion_depto_filtrada = poblacion_depto[poblacion_depto["ano"] == anio]

    # Unir con los datos de población
    merge_depto = merge_depto.merge(
        poblacion_depto_filtrada,
        left_on='COD_DEPTO',
        right_on='juri',
        how='inner'
    )

    merge_depto["CANTIDAD"] = merge_depto["CANTIDAD"].fillna(0)

    if metrica == "Tasa x100k":
        merge_depto["TASA"] = (merge_depto["CANTIDAD"] / merge_depto["poblacion"]) * 100000
        merge_depto["TASA"] = merge_depto["TASA"].round(2)  # Redondear a 2 decimales
        color_col_depto = "TASA"
        title_depto = f"Tasa x100k - {evento} (Departamento)"
    else:
        color_col_depto = "CANTIDAD"
        title_depto = f"Casos - {evento} (Departamento)"

    fig_depto = px.choropleth_mapbox(
        merge_depto,
        geojson=merge_depto.geometry.__geo_interface__,
        locations=merge_depto.index,
        color=color_col_depto,
        hover_name="DEPARTAMENTO",
        hover_data={"PROVINCIA": True, color_col_depto: ':.2f' if metrica == "Tasa x100k" else True, "poblacion": True, "CANTIDAD": True},
        mapbox_style="carto-positron",
        center={"lat": -40.0, "lon": -60.0},
        zoom=3,
        color_continuous_scale="Reds" if metrica == "Casos" else "Blues"
    )
    fig_depto.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        title_text=title_depto,
        title_x=0.5
    )
    st.plotly_chart(fig_depto, use_container_width=True, config={'displayModeBar': False})

    # Tabla Departamento
    if not merge_depto.empty:
        tabla_depto = merge_depto[["DEPARTAMENTO", "PROVINCIA", color_col_depto, "poblacion", "CANTIDAD"]].copy()
        tabla_depto.rename(columns={color_col_depto: "Tasas", "poblacion": "Población", "CANTIDAD": "Casos", "DEPARTAMENTO": "Departamento", "PROVINCIA": "Provincia"}, inplace=True)
        tabla_depto["Departamento"] = tabla_depto["Departamento"].str.title()  # Formatear nombre de departamento
        tabla_depto["Provincia"] = tabla_depto["Provincia"].str.title()  # Formatear nombre de provincia
        tabla_depto = tabla_depto.dropna(subset=["Casos", "Población"])
        if not tabla_depto.empty:
            st.write("Datos por Departamento")
            tabla_depto_sorted = tabla_depto.sort_values("Tasas", ascending=False)  # Ordenar por Tasas
            st.dataframe(tabla_depto_sorted[["Departamento", "Provincia", "Casos", "Población", "Tasas"]], use_container_width=True)
            excel_depto, name_depto = download_excel(tabla_depto_sorted, "mapa_departamento.xlsx")
            st.download_button("Descargar Excel Departamento", excel_depto, name_depto)
