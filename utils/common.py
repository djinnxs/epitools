# utils/common.py
import os
import pyodbc
import streamlit as st
import pandas as pd
import io
import duckdb
from dotenv import load_dotenv
import locale

load_dotenv()

# Configurar locale para números con punto de miles
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

def format_number(number):
    try:
        if pd.notnull(number) and isinstance(number, (int, float)):
            return locale.format_string('%.0f', float(number), grouping=True)
        return ''
    except (ValueError, TypeError):
        return str(number) if number is not None else ''

def get_sql_connection():
    try:
        conn_str = (
            r'DRIVER={SQL Server};'
            r'SERVER=SQLVIGILANCIA;'
            r'DATABASE=SNVS2;'
            r'UID=jtapia;'
            r'PWD=Kc4bb2jhww$;'
        )
        return pyodbc.connect(conn_str)
    except Exception as e:
        st.error(f"Error de conexión SQL: {e}")
        return None

@st.cache_data(ttl=3600)
def load_sql_data(query, params=None):
    conn = get_sql_connection()
    if not conn:
        return pd.DataFrame()
    try:
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error en consulta: {e}")
        return pd.DataFrame()

# --- DUCKDB / PARQUET HELPERS ---

def get_project_root():
    """Encuentra la raíz del proyecto buscando README.md hacia arriba."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != os.path.dirname(current_dir):  # Hasta llegar a root
        if os.path.exists(os.path.join(current_dir, 'README.md')):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    # Fallback: asume que utils/ está en el root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_data_path(*subpath):
    """Obtiene la ruta absoluta a un archivo en data/, relativo a la raíz del proyecto."""
    return os.path.join(get_project_root(), 'data', *subpath)

def get_parquet_path(filename='base_semanal.parquet'):
    # Usar la raíz del proyecto para rutas consistentes
    return get_data_path(filename)

def check_parquet_exists(filename='base_semanal.parquet'):
    path = get_parquet_path(filename)
    if not os.path.exists(path):
        st.error(f"⚠️ No se encontró el archivo de datos optimizado (`data/{filename}`).")
        st.info("Por favor, ejecuta el script `etl_semanal.py` para generar los datos.")
        st.stop()
    return path

def query_duckdb(query, filename='base_semanal.parquet'):
    """
    Ejecuta una consulta SQL sobre un archivo Parquet usando DuckDB.
    Reemplaza automáticamente {parquet} en la query con la ruta al archivo.
    Usa una conexión aislada para evitar problemas de concurrencia.
    """
    path = check_parquet_exists(filename)
    # Sanitize path for DuckDB (Windows backslashes can cause issues)
    path = path.replace('\\', '/')
    try:
        # Reemplazar placeholder con la ruta sanitizada para SQL
        formatted_query = query.replace('{parquet}', f"'{path}'")
        # Usar conexión aislada
        with duckdb.connect() as con:
            return con.execute(formatted_query).df()
    except Exception as e:
        st.error(f"Error consultando DuckDB: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_distinct_years():
    # Intentar usar Parquet si existe, sino SQL
    try:
        path = get_parquet_path()
        if os.path.exists(path):
            # Sanitize path for DuckDB
            path = path.replace('\\', '/')
            query = f"SELECT DISTINCT ANIO FROM '{path}' ORDER BY ANIO DESC"
            with duckdb.connect() as con:
                df = con.execute(query).df()
            return df['ANIO'].tolist()
    except:
        pass
    
    # Fallback a SQL
    query = 'SELECT DISTINCT ANIO FROM [SNVS2].[dbo].[DashClinica2] ORDER BY ANIO DESC'
    df = load_sql_data(query)
    if not df.empty:
        return df['ANIO'].tolist()
    return []

@st.cache_data(ttl=3600)
def get_distinct_events():
    # Intentar usar Parquet si existe, sino SQL
    try:
        path = get_parquet_path()
        if os.path.exists(path):
            # Sanitize path for DuckDB
            path = path.replace('\\', '/')
            query = f"SELECT DISTINCT NOMBREEVENTOAGRP FROM '{path}' ORDER BY NOMBREEVENTOAGRP"
            with duckdb.connect() as con:
                df = con.execute(query).df()
            return df['NOMBREEVENTOAGRP'].tolist()
    except:
        pass

    query = 'SELECT DISTINCT NOMBREEVENTOAGRP FROM [SNVS2].[dbo].[DashClinica2] ORDER BY NOMBREEVENTOAGRP'
    df = load_sql_data(query)
    if not df.empty:
        return df['NOMBREEVENTOAGRP'].tolist()
    return []

@st.cache_data(ttl=3600)
def get_distinct_provinces():
    # Intentar usar Parquet si existe, sino SQL
    try:
        path = get_parquet_path()
        if os.path.exists(path):
            # Sanitize path for DuckDB
            path = path.replace('\\', '/')
            query = f"SELECT DISTINCT PROVINCIA FROM '{path}' ORDER BY PROVINCIA"
            with duckdb.connect() as con:
                df = con.execute(query).df()
            return df['PROVINCIA'].tolist()
    except:
        pass

    query = 'SELECT DISTINCT PROVINCIA FROM [SNVS2].[dbo].[DashClinica2] ORDER BY PROVINCIA'
    df = load_sql_data(query)
    if not df.empty:
        return df['PROVINCIA'].tolist()
    return []


@st.cache_data(ttl=3600)
def load_population_province(year: int | None = None):
    """Load and normalize provincial population data.
    Prefers parquet files under data/parquet or data/*.parquet, falls back to CSV.
    Returns DataFrame with at least columns: ano (int), juri (2-digit str), juri_nombre, poblacion (int).
    If year is provided, filters by that year.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    candidates = [
        os.path.join(data_dir, 'parquet', 'poblacionxprovinciaindec.parquet'),
        os.path.join(data_dir, 'poblacionxprovinciaindec.parquet'),
        os.path.join(data_dir, 'poblacionxprovinciaindec.csv')
    ]
    df = pd.DataFrame()
    for p in candidates:
        if os.path.exists(p):
            try:
                if p.endswith('.parquet'):
                    df = pd.read_parquet(p)
                else:
                    df = pd.read_csv(p)
            except Exception:
                continue
            # Normalize columns
            if 'ano' in df.columns:
                df['ano'] = df['ano'].astype(int)
            if 'poblacion' in df.columns:
                df['poblacion'] = pd.to_numeric(df['poblacion'], errors='coerce').fillna(0).astype(int)
            if 'juri' in df.columns:
                df['juri'] = df['juri'].astype(str).str.zfill(2)
            elif 'juri_codigo' in df.columns:
                df['juri'] = df['juri_codigo'].astype(str).str.zfill(2)
            # ensure juri_nombre exists
            if 'juri_nombre' not in df.columns and 'jur_nombre' in df.columns:
                df = df.rename(columns={'jur_nombre': 'juri_nombre'})
            if year is not None and 'ano' in df.columns:
                df = df[df['ano'] == int(year)]
            return df
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_population_department(year: int | None = None):
    """Load and normalize departmental population data.
    Prefers parquet files under data/parquet or data/*.parquet, falls back to CSV.
    Returns DataFrame with columns: ano, cod_depto (5-digit str), juri_nombre, departamento_nombre, poblacion.
    If year is provided, filters by that year.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    candidates = [
        os.path.join(data_dir, 'parquet', 'proyecciones_depto_indec.parquet'),
        os.path.join(data_dir, 'proyecciones_depto_indec.parquet'),
        os.path.join(data_dir, 'proyecciones_depto_indec.csv')
    ]
    df = pd.DataFrame()
    for p in candidates:
        if os.path.exists(p):
            try:
                if p.endswith('.parquet'):
                    df = pd.read_parquet(p)
                else:
                    df = pd.read_csv(p, sep=';')
            except Exception:
                continue
            # Normalize
            if 'ano' in df.columns:
                df['ano'] = df['ano'].astype(int)
            if 'poblacion' in df.columns:
                df['poblacion'] = pd.to_numeric(df['poblacion'], errors='coerce').fillna(0).astype(int)
            # Build cod_depto if missing
            if 'cod_depto' not in df.columns:
                if 'juri_codigo' in df.columns and 'departamento_codigo' in df.columns:
                    df['cod_depto'] = df['juri_codigo'].astype(str).str.zfill(2) + df['departamento_codigo'].astype(str).str.zfill(3)
                elif 'juri' in df.columns and 'departamento_codigo' in df.columns:
                    df['cod_depto'] = df['juri'].astype(str).str.zfill(2) + df['departamento_codigo'].astype(str).str.zfill(3)
                elif 'juri' in df.columns and 'departamento_nombre' in df.columns and 'departamento_codigo' not in df.columns:
                    # fallback: if juri already contains 5-digit, use it
                    if df['juri'].astype(str).str.len().max() >= 5:
                        df['cod_depto'] = df['juri'].astype(str)
            # Zero-fill
            if 'cod_depto' in df.columns:
                df['cod_depto'] = df['cod_depto'].astype(str).str.zfill(5)
            # Ensure names
            if 'juri_nombre' not in df.columns and 'jur_nombre' in df.columns:
                df = df.rename(columns={'jur_nombre': 'juri_nombre'})
            if year is not None and 'ano' in df.columns:
                df = df[df['ano'] == int(year)]
            return df
    return pd.DataFrame()

def style_table(df, cmap="Blues"):
    return df.style.background_gradient(cmap=cmap).format(format_number)

def download_csv(df, filename):
    csv = df.to_csv(index=False).encode('utf-8')
    return csv, filename

def download_excel(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    return output.getvalue(), filename