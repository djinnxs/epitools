# utils/common.py
import os
import streamlit as st
import pandas as pd
import io
import duckdb
import pyodbc
from dotenv import load_dotenv
import locale

load_dotenv()

# Configurar locale para números con punto de miles
# En la nube (Linux), es más seguro usar 'en_US.UTF-8' o manejarlo manualmente si falla
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass

def format_number(number, decimals=0):
    try:
        if pd.notnull(number) and isinstance(number, (int, float)):
            if decimals == 0:
                return f"{int(number):,}".replace(",", ".")
            else:
                # Formateo para decimales: 1.234,56
                formatted = f"{float(number):,.{decimals}f}"
                # Intercambiar comas y puntos
                # Usamos un placeholder temporal
                return formatted.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return ''
    except (ValueError, TypeError):
        return str(number) if number is not None else ''

def style_argentina(styler, numeric_cols=None):
    """Aplica formato argentino (punto para miles, coma para decimales) a un Pandas Styler."""
    if numeric_cols is None:
        numeric_cols = styler.data.select_dtypes(include=['number']).columns.tolist()
    
    formats = {}
    for col in numeric_cols:
        # Si la columna es float y tiene valores decimales, usamos 2 decimales
        if styler.data[col].dtype == 'float64' and (styler.data[col] % 1 != 0).any():
             formats[col] = "{:,.2f}"
        else:
             formats[col] = "{:,.0f}"
             
    return styler.format(formats, thousands='.', decimal=',')

# --- DUCKDB / PARQUET HELPERS ---

def get_parquet_path(filename='base_semanal.parquet'):
    """
    Obtiene la ruta absoluta al archivo parquet dentro de la carpeta 'data'.
    Funciona correctamente en despliegues de Streamlit Cloud.
    """
    # Detecta la raíz del proyecto (un nivel arriba de /utils)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'data', filename)

def check_parquet_exists(filename='base_semanal.parquet'):
    path = get_parquet_path(filename)
    if not os.path.exists(path):
        st.error(f"⚠️ No se encontró el archivo de datos (`data/{filename}`).")
        st.info("Asegúrate de que el archivo esté en el repositorio de GitHub dentro de la carpeta 'data'.")
        st.stop()
    return path

def query_duckdb(query, filename='base_semanal.parquet'):
    """
    Ejecuta consulta SQL sobre Parquet usando DuckDB.
    """
    path = check_parquet_exists(filename)
    # Sanitizar ruta para DuckDB (Linux/Cloud usa forward slashes)
    path = path.replace('\\', '/')
    try:
        formatted_query = query.replace('{parquet}', f"'{path}'")
        with duckdb.connect() as con:
            return con.execute(formatted_query).df()
    except Exception as e:
        st.error(f"Error consultando DuckDB: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_distinct_years():
    try:
        path = get_parquet_path().replace('\\', '/')
        if os.path.exists(path):
            query = f"SELECT DISTINCT ANIO FROM '{path}' WHERE ANIO IS NOT NULL ORDER BY ANIO DESC"
            with duckdb.connect() as con:
                df = con.execute(query).df()
            return df['ANIO'].astype(int).tolist()
    except Exception as e:
        st.warning(f"No se pudieron cargar años del archivo local.")
    return []

@st.cache_data(ttl=3600)
def get_distinct_events():
    try:
        path = get_parquet_path().replace('\\', '/')
        if os.path.exists(path):
            query = f"SELECT DISTINCT NOMBREEVENTOAGRP FROM '{path}' WHERE NOMBREEVENTOAGRP IS NOT NULL ORDER BY NOMBREEVENTOAGRP"
            with duckdb.connect() as con:
                df = con.execute(query).df()
            return df['NOMBREEVENTOAGRP'].tolist()
    except Exception as e:
        st.warning("No se pudieron cargar eventos del archivo local.")
    return []

@st.cache_data(ttl=3600)
def get_distinct_provinces():
    try:
        path = get_parquet_path().replace('\\', '/')
        if os.path.exists(path):
            query = f"SELECT DISTINCT PROVINCIA FROM '{path}' WHERE PROVINCIA IS NOT NULL ORDER BY PROVINCIA"
            with duckdb.connect() as con:
                df = con.execute(query).df()
            return df['PROVINCIA'].tolist()
    except Exception as e:
        pass
    return []

@st.cache_data(ttl=3600)
def get_distinct_departments():
    try:
        path = get_parquet_path().replace('\\', '/')
        if os.path.exists(path):
            query = f"SELECT DISTINCT DEPARTAMENTO FROM '{path}' WHERE DEPARTAMENTO IS NOT NULL ORDER BY DEPARTAMENTO"
            with duckdb.connect() as con:
                df = con.execute(query).df()
            return df['DEPARTAMENTO'].tolist()
    except Exception as e:
        pass
    return []

@st.cache_data(ttl=3600)
def load_population_province(year: int | None = None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    candidates = [
        os.path.join(data_dir, 'poblacionxprovinciaindec.parquet'),
        os.path.join(data_dir, 'parquet', 'poblacionxprovinciaindec.parquet')
    ]
    
    for p in candidates:
        if os.path.exists(p):
            try:
                df = pd.read_parquet(p)
                # Normalización básica
                if 'ano' in df.columns:
                    df['ano'] = df['ano'].astype(int)
                    if year:
                        df = df[df['ano'] == int(year)]
                return df
            except:
                continue
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_population_department(year: int | None = None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    p = os.path.join(data_dir, 'proyecciones_depto_indec.parquet')
    
    if os.path.exists(p):
        try:
            df = pd.read_parquet(p)
            if year and 'ano' in df.columns:
                df = df[df['ano'] == int(year)]
            return df
        except:
            pass
    return pd.DataFrame()

def style_table(df, cmap="Blues"):
    return df.style.background_gradient(cmap=cmap)

def download_csv(df, filename):
    csv = df.to_csv(index=False).encode('utf-8')
    return csv, filename

def download_excel(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    return output.getvalue(), filename

def load_sql_data(query):
    """
    Carga datos desde SQL Server usando las credenciales del archivo .env
    """
    server = os.getenv('SQL_SERVER')
    database = os.getenv('SQL_DATABASE')
    username = os.getenv('SQL_UID')
    password = os.getenv('SQL_PWD')
    
    # Connection string para pyodbc
    conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    
    try:
        conn = pyodbc.connect(conn_str)
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error conectando a SQL Server: {e}")
        st.error(f"Error conectando a SQL Server: {e}")
        return pd.DataFrame()

# --- SEMANA EPIDEMIOLÓGICA Y CORTE DE DATOS ---
# (helpers compartidos con epitoolsnac: ranking, retraso de reporte, boletín)

from datetime import date, timedelta

def get_epi_week(fecha):
    """Semana epidemiológica (semanas inician en domingo; la SE1 contiene el 4 de enero)."""
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

def get_epi_week_data(fecha):
    """Devuelve (semana, año epidemiológico) para una fecha."""
    anio = fecha.year

    def inicio_se_1(year):
        cuatro_enero = date(year, 1, 4)
        retroceso = (cuatro_enero.weekday() + 1) % 7
        return cuatro_enero - timedelta(days=retroceso)

    inicio_actual = inicio_se_1(anio)
    if fecha < inicio_actual:
        inicio_anterior = inicio_se_1(anio - 1)
        dias = (fecha - inicio_anterior).days
        return (dias // 7) + 1, anio - 1
    inicio_proximo = inicio_se_1(anio + 1)
    if fecha >= inicio_proximo:
        return 1, anio + 1
    dias = (fecha - inicio_actual).days
    return (dias // 7) + 1, anio

def epiweek_to_date(anio, semana):
    """Fecha de inicio (domingo) de la semana epidemiológica."""
    four_jan = date(anio, 1, 4)
    start_se1 = four_jan - timedelta(days=(four_jan.weekday() + 1) % 7)
    return start_se1 + timedelta(weeks=semana - 1)

@st.cache_data(ttl=3600)
def get_data_corte(filename='base_semanal.parquet'):
    """Último corte disponible en la base:
    {'anio', 'semana', 'fecha_inicio', 'fecha_fin'} o None si no hay datos."""
    try:
        path = get_parquet_path(filename)
        if not os.path.exists(path):
            return None
        df = pd.read_parquet(path, columns=['ANIO', 'SEMANA'])
        if df.empty:
            return None
        anio = int(df['ANIO'].max())
        semana = int(df.loc[df['ANIO'] == anio, 'SEMANA'].max())
        inicio = epiweek_to_date(anio, semana)
        return {
            'anio': anio,
            'semana': semana,
            'fecha_inicio': inicio,
            'fecha_fin': inicio + timedelta(days=6),  # sábado = fin de la SE
        }
    except Exception:
        return None

def show_data_corte(prefix='📊 Datos hasta'):
    """Muestra el corte de datos como pie de página en cualquier página."""
    c = get_data_corte()
    if c:
        st.caption(f"{prefix} {c['fecha_fin'].strftime('%d/%m/%Y')} · "
                   f"semana epidemiológica {c['semana']} de {c['anio']}")
    else:
        st.caption("⚠️ No se pudo determinar el corte de datos.")

# --- ESTILO VISUAL COMPARTIDO ---
# Paleta y helpers para que todos los gráficos nuevos tengan la misma
# identidad visual (referencias: OWID, CDC, ECDC).

PALETA = [
    "#1f77b4", "#e94560", "#2ca02c", "#ff7f0e", "#9467bd",
    "#17becf", "#8c564b", "#bcbd22", "#7f7f7f", "#d62728",
]

# Escala bivariada 3x3 (filas = incidencia, columnas = tendencia).
BIVAR_COLORS = {
    "Inc. baja · Tend. baja": "#e8e8e8",
    "Inc. baja · Tend. estable": "#b5c0da",
    "Inc. baja · Tend. alta": "#6c83b5",
    "Inc. media · Tend. baja": "#b8d6be",
    "Inc. media · Tend. estable": "#90b2b3",
    "Inc. media · Tend. alta": "#567994",
    "Inc. alta · Tend. baja": "#73ae80",
    "Inc. alta · Tend. estable": "#5a9178",
    "Inc. alta · Tend. alta": "#2a5a5b",
}

def show_semana_actual():
    """Banner uniforme con la semana epidemiológica actual.

    Se muestra en todas las páginas justo debajo del título, con el mismo
    estilo que ya usaban algunas (fondo oscuro, texto amarillo).
    """
    hoy = date.today()
    semana, anio_epi = get_epi_week_data(hoy)
    st.markdown(
        f"""<div style="background-color: #1a1a2e; color: #ffeb3b;
        padding: 10px 14px; border-radius: 8px; margin-bottom: 18px;
        border: 1px solid #4a6fa5; text-align: center; font-weight: 600;
        font-size: 1.05rem;">
        📅 Semana Epidemiológica Actual: <b>{semana}</b> del {anio_epi}
        </div>""",
        unsafe_allow_html=True,
    )

def style_fig(fig, height=420, titulo=None, x_title=None, y_title=None,
              hovermode="x unified", mostrar_leyenda=True):
    """Aplica el estilo visual común a una figura Plotly (tema claro, paleta fija)."""
    fig.update_layout(
        template="plotly_white",
        colorway=PALETA,
        height=height,
        margin=dict(l=10, r=10, t=60 if titulo else 25, b=10),
        font=dict(family="sans-serif", size=12),
        hovermode=hovermode,
        showlegend=mostrar_leyenda,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    if titulo:
        fig.update_layout(title=dict(text=titulo, x=0.5, xanchor="center"))
    if x_title:
        fig.update_xaxes(title_text=x_title)
    if y_title:
        fig.update_yaxes(title_text=y_title)
    return fig
