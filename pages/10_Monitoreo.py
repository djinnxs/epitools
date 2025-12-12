import streamlit as st
import pandas as pd
from datetime import date
import io
from utils.common import query_duckdb, get_distinct_years
import duckdb

st.set_page_config(page_title="Epidemiologia", page_icon=":bar_chart:", layout="wide")

# Solo el título sin logo
st.markdown('<center><h3 style="font-weight:bold; padding:5px; border-radius:6px; width:100%;">🔎 Monitoreo de Notificación</h3></center>', unsafe_allow_html=True)

# Obtiene la semana actual
SemanActual = date.today().isocalendar()[1]

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
    nivel = st.radio("Seleccione Nivel", ["Provincia", "Departamento"], horizontal=True)

# Cargar datos base filtrados por año
# Usamos monitor_clinica.parquet
query_base = f"""
SELECT ORIGEN, CODIGO_DEPTO, DEPARTAMENTO, CODIGO_PROVINCIA, PROVINCIA, ANIO, SEMANA, ESTADO, FECHAREGISTROENCABEZADO, CANTIDAD
FROM {{parquet}}
WHERE ANIO = {anio}
"""
df = query_duckdb(query_base, filename='monitor_clinica.parquet')

if df.empty:
    st.warning(f"⚠️ No se encontraron datos para el año {anio}. Por favor ejecuta el ETL.")
    st.stop()

# --- LÓGICA NIVEL PROVINCIA ---
if nivel == "Provincia":
    # Filtro Provincia
    provincias = sorted(df["PROVINCIA"].unique())
    idx_ba = provincias.index("Buenos Aires") if "Buenos Aires" in provincias else 0
    provincia_seleccionada = st.selectbox("Provincia", provincias, index=idx_ba)

    # Filtro Departamento (dentro de provincia)
    deptos_prov = sorted(df[df["PROVINCIA"] == provincia_seleccionada]["DEPARTAMENTO"].unique().tolist())
    departamento_seleccionado = st.selectbox(
        "Departamento",
        ["Todos los departamentos"] + deptos_prov,
    )

    # Filtrar DF
    if departamento_seleccionado != "Todos los departamentos":
        df_filtered = df[(df["PROVINCIA"] == provincia_seleccionada) & (df["DEPARTAMENTO"] == departamento_seleccionado)]
    else:
        df_filtered = df[df["PROVINCIA"] == provincia_seleccionada]

    if df_filtered.empty:
        st.warning("No hay datos para la selección.")
        st.stop()

    # Pivot Table
    pivot_table = df_filtered.pivot_table(
        values="CANTIDAD", index="ORIGEN", columns="SEMANA", aggfunc="first"
    ).fillna(0)

    pivot_table = pivot_table.reindex(columns=range(1, 53), fill_value=0)

    # Estilos
    def style_cell(val):
        if val == 0:
            return "background-color: #0000FF"  # Azul (según código usuario)
        elif val > 0:
            return "background-color: #008000"  # Verde
        else:
            return "background-color: #FF0000"  # Rojo

    styled_table = pivot_table.style.map(style_cell).format("{:.0f}")

    # Indicadores
    regularidad = df_filtered[df_filtered["SEMANA"] <= SemanaO].groupby("ORIGEN")["SEMANA"].nunique()
    ultima_semana_con_datos = df_filtered.groupby("ORIGEN")["SEMANA"].max()

    if regularidad.empty:
        nueva_tabla = pd.DataFrame({"Establecimiento": [], "Regularidad": [], "Oportunidad": []})
    else:
        nueva_tabla = pd.DataFrame({
            "Establecimiento": regularidad.index,
            "Regularidad": regularidad.values,
            "Oportunidad": SemanaO - ultima_semana_con_datos
        })
        nueva_tabla.loc[nueva_tabla["Oportunidad"] < 0, "Oportunidad"] = 0
        nueva_tabla["Regularidad"] = (nueva_tabla["Regularidad"] * 100) / SemanaO

    cobertura = (nueva_tabla["Regularidad"] >= 50).sum() / len(nueva_tabla) if len(nueva_tabla) > 0 else 0
    notificacion_nula = (pivot_table == 0).sum().sum() / (pivot_table.shape[0] * pivot_table.shape[1]) if (pivot_table.shape[0] * pivot_table.shape[1]) > 0 else 0
    mediana_oportunidad = nueva_tabla["Oportunidad"].median() if not nueva_tabla["Oportunidad"].empty else 0
    mediana_regularidad = nueva_tabla["Regularidad"].median() if not nueva_tabla["Regularidad"].empty else 0

    # Título dinámico
    if departamento_seleccionado != "Todos los departamentos":
        titulo = f"Semana actual: {SemanActual} - Tabla de Monitoreo ({departamento_seleccionado}), {provincia_seleccionada} - Regularidad: {mediana_regularidad:.2f}% - Oportunidad: {mediana_oportunidad:.2f} - Cobertura: {cobertura:.2%} - Notificación nula: {notificacion_nula:.2%}"
    else:
        titulo = f"Semana actual: {SemanActual} - Tabla de Monitoreo - {provincia_seleccionada} - Regularidad: {mediana_regularidad:.2f}% - Oportunidad: {mediana_oportunidad:.2f} - Cobertura: {cobertura:.2%} - Notificación nula: {notificacion_nula:.2%}"

    st.markdown(f"<h3 style='text-align: center;'>{titulo}</h3>", unsafe_allow_html=True)

    # Mostrar Tabla
    st.write(styled_table.set_table_styles([
        {'selector': 'th', 'props': [('font-size', '14px'), ('width', '100px')]},
        {'selector': 'td', 'props': [('font-size', '14px'), ('width', '30px')]}
    ]).to_html(), unsafe_allow_html=True)

    # Descarga Excel Monitoreo
    def download_excel(df, file_name):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=True)
        return output.getvalue(), file_name

    excel_data, file_name = download_excel(pivot_table, "Monitoreo.xlsx")
    st.download_button(
        " Descargar Excel de Monitoreo",
        data=excel_data,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help='Haz clic aquí para descargar el archivo Excel'
    )

    st.markdown("## Regularidad y Oportunidad de Notificación")
    st.write(nueva_tabla)

    excel_data_nueva_tabla, file_name_nueva_tabla = download_excel(nueva_tabla, "Regularidad y oportunidad.xlsx")
    st.download_button(
        " Descargar Excel de Regularidad y Oportunidad",
        data=excel_data_nueva_tabla,
        file_name=file_name_nueva_tabla,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help='Haz clic aquí para descargar el archivo Excel'
    )

# --- LÓGICA NIVEL DEPARTAMENTO ---
else: # Nivel Departamento
    # Filtro Provincia
    provincias = sorted(df["PROVINCIA"].unique())
    idx_ba = provincias.index("Buenos Aires") if "Buenos Aires" in provincias else 0
    provincia_seleccionada = st.selectbox("Provincia", provincias, index=idx_ba)

    if provincia_seleccionada != "NACION":
        df_filtered = df[df["PROVINCIA"] == provincia_seleccionada]
    else:
        df_filtered = df.copy()

    if df_filtered.empty:
        st.warning("No hay datos para la selección.")
        st.stop()

    # Pivot Table (para cálculos internos)
    pivot_table = df_filtered.pivot_table(
        values="CANTIDAD", index="ORIGEN", columns="SEMANA", aggfunc="first"
    )
    pivot_table = pivot_table.reindex(columns=range(1, 53))

    # Cálculos
    regularidad = df_filtered[df_filtered["SEMANA"] <= SemanaO].groupby(["DEPARTAMENTO", "ORIGEN"])["SEMANA"].nunique()
    ultima_semana_con_datos = df_filtered.groupby(["DEPARTAMENTO", "ORIGEN"])["SEMANA"].max()

    nueva_tabla = pd.DataFrame({
        "Departamento": regularidad.index.get_level_values("DEPARTAMENTO"),
        "Origen": regularidad.index.get_level_values("ORIGEN"),
        "Regularidad": regularidad.values,
        "Oportunidad": SemanaO - ultima_semana_con_datos.values
    })
    nueva_tabla.loc[nueva_tabla["Oportunidad"] < 0, "Oportunidad"] = 0
    nueva_tabla["Regularidad"] = (nueva_tabla["Regularidad"] * 100) / SemanaO

    # Mediana por Departamento
    mediana_regularidad = nueva_tabla.groupby("Departamento")["Regularidad"].median()
    mediana_oportunidad = nueva_tabla.groupby("Departamento")["Oportunidad"].median()

    # Cobertura y Notificación Nula por Departamento
    departamentos = mediana_regularidad.index
    cobertura = []
    notificacion_nula = []

    for departamento in departamentos:
        df_departamento = nueva_tabla[nueva_tabla["Departamento"] == departamento]
        
        # Cobertura
        if len(df_departamento) > 0:
            cobertura_departamento = (df_departamento["Regularidad"] >= 50).sum() / len(df_departamento)
        else:
            cobertura_departamento = 0
        cobertura.append(cobertura_departamento)
        
        # Notificación Nula
        # Necesitamos los origenes de este departamento para buscar en pivot_table
        origenes_depto = df_departamento["Origen"]
        # Intersección con pivot_table index (por si acaso)
        origenes_validos = origenes_depto[origenes_depto.isin(pivot_table.index)]
        
        if len(origenes_validos) > 0:
            # Contar ceros en las semanas hasta SemanaO (o todas? el usuario usó pivot_table.shape[1] * SemanaO en el denominador, pero pivot_table tiene 52 columnas)
            # El usuario usó: (pivot_table.loc[...] == 0).sum() / (pivot_table.shape[1] * SemanaO)
            # Esto es un poco extraño dimensionalmente (cols * SemanaO?), pero replicaré su lógica.
            # Espera, pivot_table.shape[1] es 52. SemanaO es un escalar.
            # El usuario dividió por (52 * SemanaO). Asumiré que quiso decir (num_filas * SemanaO) o (num_filas * 52).
            # En su código nivel provincia: (pivot_table == 0).sum().sum() / (pivot_table.shape[0] * pivot_table.shape[1]) -> ceros / total_celdas.
            # En su código nivel departamento: (pivot_table.loc[...] == 0).sum() / (pivot_table.shape[1] * SemanaO)
            # (pivot_table.loc[...] == 0).sum() devuelve una serie (suma por columna) o un escalar (suma total)? .values == 0 devuelve matriz booleana. .sum() devuelve escalar total.
            # Replicaré literalmente:
            notificacion_nula_departamento = (pivot_table.loc[origenes_validos, :].values == 0).sum() / (pivot_table.shape[1] * SemanaO) if SemanaO > 0 else 0
        else:
            notificacion_nula_departamento = 0
        
        notificacion_nula.append(notificacion_nula_departamento)

    # Tabla Final
    tabla_departamentos = pd.DataFrame({
        "Departamento": departamentos,
        "Regularidad (Mediana)": mediana_regularidad.values,
        "Oportunidad (Mediana)": mediana_oportunidad.values,
        "Cobertura": cobertura,
        "Notificación nula": notificacion_nula
    })

    st.markdown(f"## Indicadores de {provincia_seleccionada}")
    st.write(tabla_departamentos)

    # Descarga
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        tabla_departamentos.to_excel(writer, index=False, sheet_name='Indicadores')
    data = output.getvalue()

    st.download_button(
        "📊 Descargar Excel de Monitoreo Departamental",
        data=data,
        file_name="Monitoreo departamental.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help='Haz clic aquí para descargar el archivo Excel'
    )