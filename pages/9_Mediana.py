# pages/9_Mediana.py
import pandas as pd
import streamlit as st
import io
import locale
from utils.common import query_duckdb, get_distinct_events, get_distinct_years

st.set_page_config(page_title="Mediana", page_icon=":pencil:", layout="wide")

# Configurar la configuración regional
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

# Función para formatear números sin decimales, usando punto para miles y coma para decimales
def format_number(number):
    try:
        return locale.format_string('%.0f', number, grouping=True)
    except:
        return str(int(number)) if pd.notnull(number) else ''

st.markdown('<center><h3 style="font-weight:bold; padding:5px; border-radius:6px; width:100%;"> Índice epidémico 📝 </h3></center>', unsafe_allow_html=True)

# Cargar filtros
events = get_distinct_events()
years = get_distinct_years()

# Filtros en columnas
col1, col2, col3 = st.columns(3)
with col1:
    evento = st.multiselect("Elije el Evento", events)
with col2:
    # Si no hay años en el parquet, fallback a lista manual o año actual
    if not years:
        years = [2024, 2023, 2022, 2021, 2020, 2019]
    year = st.selectbox("Selecciona el Año", years)
with col3:
    semana = st.selectbox("Selecciona la Semana", range(1, 53))

calcular_tabla = st.button("Calcular Tabla")

if calcular_tabla:
    if not evento:
        st.warning("Por favor selecciona al menos un evento.")
        st.stop()

    # Construir lista de años para la query (año seleccionado y 4 anteriores)
    years_filter = [year, year - 1, year - 2, year - 3, year - 4]
    years_str = ",".join(map(str, years_filter))
    
    # Formatear eventos para SQL
    events_str = "', '".join(evento)
    
    # DuckDB query
    # Traemos datos crudos para procesar en Pandas igual que el original
    query = f"""
    SELECT CODIGO_PROVINCIA, PROVINCIA, ANIO, SEMANA, ID_SNVS_EVENTO_AGRP,
           NOMBREEVENTOAGRP, IDEDAD, GRUPO, CANTIDAD, FECHAREGISTROCLINICA
    FROM {{parquet}}
    WHERE ANIO IN ({years_str})
      AND NOMBREEVENTOAGRP IN ('{events_str}')
      AND SEMANA != 53
    """
    
    clinica = query_duckdb(query)
    
    if clinica.empty:
        st.warning("No hay datos para los filtros seleccionados.")
    else:
        # Lógica original del usuario
        clinica.sort_values(['NOMBREEVENTOAGRP', 'PROVINCIA'], inplace=True)
        clinica.reset_index(drop=True, inplace=True)

        df_agrupado = clinica.groupby(['PROVINCIA', 'ANIO', 'SEMANA', 'NOMBREEVENTOAGRP'], as_index=False).agg({
            'CODIGO_PROVINCIA': 'first',
            'IDEDAD': 'first',
            'GRUPO': 'first',
            'CANTIDAD': 'sum'
        })

        df_agrupado = df_agrupado.sort_values(by=['PROVINCIA', 'ANIO']).reset_index(drop=True)
        
        df_filtrado = df_agrupado # Ya filtrado

        df_semana = df_filtrado[df_filtrado['SEMANA'] == semana]
        df_acumulado = df_filtrado[df_filtrado['SEMANA'] <= semana]

        df_semana = df_semana.groupby(['PROVINCIA', 'ANIO'], as_index=False)['CANTIDAD'].sum()
        df_acumulado = df_acumulado.groupby(['PROVINCIA', 'ANIO'], as_index=False)['CANTIDAD'].sum()

        df_declarados = df_semana.pivot(index='PROVINCIA', columns='ANIO', values='CANTIDAD')
        df_acumulados = df_acumulado.pivot(index='PROVINCIA', columns='ANIO', values='CANTIDAD')

        df_mediana_sem = df_semana.groupby('PROVINCIA')['CANTIDAD'].median()
        df_mediana_acum = df_acumulado.groupby('PROVINCIA')['CANTIDAD'].sum() / df_acumulado.groupby('PROVINCIA').size()
        
        df_indice_epidemico_sem = df_semana.set_index('PROVINCIA')['CANTIDAD'] / df_mediana_sem
        df_indice_epidemico_acum = df_acumulado.groupby('PROVINCIA')['CANTIDAD'].sum() / df_mediana_acum

        all_provinces = pd.Index(df_declarados.index.union(df_acumulados.index).union(df_mediana_sem.index).union(df_mediana_acum.index)).drop_duplicates()

        # Reindexar series (con deduplicación previa para evitar ValueError)
        df_mediana_sem = df_mediana_sem.loc[~df_mediana_sem.index.duplicated(keep='first')].reindex(all_provinces)
        df_mediana_acum = df_mediana_acum.loc[~df_mediana_acum.index.duplicated(keep='first')].reindex(all_provinces)
        df_indice_epidemico_sem = df_indice_epidemico_sem.loc[~df_indice_epidemico_sem.index.duplicated(keep='first')].reindex(all_provinces)
        df_indice_epidemico_acum = df_indice_epidemico_acum.loc[~df_indice_epidemico_acum.index.duplicated(keep='first')].reindex(all_provinces)

        # Manejo de columnas dinámicas (year, year-1)
        if year in df_declarados.columns:
            col_year = df_declarados[year]
        else:
            col_year = pd.Series(0, index=all_provinces)
            
        if (year-1) in df_declarados.columns:
            col_year_prev = df_declarados[year-1]
        else:
            col_year_prev = pd.Series(0, index=all_provinces)

        if year in df_acumulados.columns:
            col_acum_year = df_acumulados[year]
        else:
            col_acum_year = pd.Series(0, index=all_provinces)

        if (year-1) in df_acumulados.columns:
            col_acum_year_prev = df_acumulados[year-1]
        else:
            col_acum_year_prev = pd.Series(0, index=all_provinces)

        df_final = pd.DataFrame({
            f'Casos declarados Sem {semana} {year-1}': col_year_prev,
            f'Casos declarados Sem {semana} {year}': col_year,
            f'Acumulados {year-1}': col_acum_year_prev,
            f'Acumulados {year}': col_acum_year,
            f'Mediana Sem {semana}': df_mediana_sem,
            'Mediana Acum.': df_mediana_acum,
            f'Índice epidémico Sem {semana}': df_indice_epidemico_sem,
            'Índice epidémico Acum.': df_indice_epidemico_acum,
        })

        # Aplicar el formato a todas las columnas numéricas
        for col in df_final.columns:
            df_final[col] = df_final[col].apply(lambda x: format_number(x) if pd.notnull(x) else x)

        # Mostrar la tabla
        st.dataframe(df_final.style.background_gradient(cmap="Blues"))

        # Botón para descargar la tabla en Excel
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df_final.to_excel(writer, sheet_name='Sheet1', index=True)
        writer.close()

        st.download_button(
            label="Descargar Tabla en Excel",
            data=output.getvalue(),
            file_name='indice_epidemico.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )