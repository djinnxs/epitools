import pandas as pd
import os
from utils.common import load_sql_data, get_data_path

def export_to_parquet():
    # Existing export_to_parquet logic remains unchanged
    pass


def convert_csv_to_parquet():
    """Convert population CSV files to Parquet for faster loading.
    Creates 'data/parquet' directory if it does not exist and writes:
    - proyecciones_depto_indec.parquet
    - poblacionxprovinciaindec.parquet
    """
    import os
    import pandas as pd

    parquet_dir = get_data_path('parquet')
    os.makedirs(parquet_dir, exist_ok=True)

    # Convert department projections
    dept_csv = get_data_path('proyecciones_depto_indec.csv')
    if os.path.exists(dept_csv):
        df_dept = pd.read_csv(dept_csv, sep=';', on_bad_lines='warn')
        dept_parquet = os.path.join(parquet_dir, 'proyecciones_depto_indec.parquet')
        df_dept.to_parquet(dept_parquet, engine='pyarrow', compression='snappy')
        print(f"Converted {dept_csv} → {dept_parquet}")
    else:
        print(f"Warning: {dept_csv} not found, skipping department conversion.")

    # Convert province population
    prov_csv = get_data_path('poblacionxprovinciaindec.csv')
    if os.path.exists(prov_csv):
        df_prov = pd.read_csv(prov_csv)
        prov_parquet = os.path.join(parquet_dir, 'poblacionxprovinciaindec.parquet')
        df_prov.to_parquet(prov_parquet, engine='pyarrow', compression='snappy')
        print(f"Converted {prov_csv} → {prov_parquet}")
    else:
        print(f"Warning: {prov_csv} not found, skipping province conversion.")

    print("Iniciando descarga de SQL (DashClinica2)...")
    # Traemos TODOS los campos necesarios para todas las páginas
    query = """
    SELECT [CODIGO_PROVINCIA], [PROVINCIA], [DEPARTAMENTO], [COD_DEPTO], 
           [ANIO], [SEMANA], [NOMBREEVENTOAGRP], [ID_SNVS_EVENTO_AGRP],
           [IDEDAD], [GRUPO], [CANTIDAD], [FECHAREGISTROCLINICA]
    FROM [SNVS2].[dbo].[DashClinica2]
    WHERE ANIO >= 2018 
    """
    
    df = load_sql_data(query) 
    
    if df.empty:
        print("Error: No se obtuvieron datos de SQL.")
        return

    print(f"Datos descargados: {len(df)} filas.")

    # Optimización de tipos de datos
    try:
        df['ANIO'] = df['ANIO'].astype('int16')
        df['SEMANA'] = df['SEMANA'].astype('int8')
        df['CANTIDAD'] = df['CANTIDAD'].fillna(0).astype('int32')
        
        # Categorías
        cols_cat = ['PROVINCIA', 'NOMBREEVENTOAGRP', 'DEPARTAMENTO', 'GRUPO']
        for col in cols_cat:
            if col in df.columns:
                df[col] = df[col].astype('category')
                
    except Exception as e:
        print(f"Advertencia durante la conversión de tipos: {e}")

    os.makedirs('data', exist_ok=True)
    
    output_path = get_data_path('base_semanal.parquet')
    print(f"Guardando a {output_path}...")
    
    try:
        df.to_parquet(output_path, engine='pyarrow', compression='snappy')
        print("¡Listo! Archivo base_semanal.parquet generado.")
    except Exception as e:
        print(f"Error guardando Parquet: {e}")

def export_climahisto():
    print("\nIniciando descarga de SQL (ClimaHisto)...")
    # Intentamos descargar la tabla climahisto si existe
    query = "SELECT * FROM [SNVS2].[dbo].[climahisto]" # Ajustar nombre si es diferente
    
    df = load_sql_data(query)
    
    if df.empty:
        print("Advertencia: No se pudo descargar climahisto o está vacía.")
        return

    print(f"Datos climahisto descargados: {len(df)} filas.")
    
    output_path = get_data_path('climahisto.parquet')
    print(f"Guardando a {output_path}...")
    
    try:
        df.to_parquet(output_path, engine='pyarrow', compression='snappy')
        print("¡Listo! Archivo climahisto.parquet generado.")
    except Exception as e:
        print(f"Error guardando climahisto Parquet: {e}")

def export_monitor_clinica():
    print("\nIniciando descarga de SQL (Monitor Clinica - Tabla CLINICA)...")
    # Traemos datos de la tabla CLINICA para el monitor detallado
    # Filtramos por año >= 2018 para tener histórico
    query = """
    SELECT [ORIGEN]
        ,[CODIGO_DEPTO]
        ,[DEPARTAMENTO]
        ,[CODIGO_PROVINCIA]
        ,[PROVINCIA]
        ,[ANIO]
        ,[SEMANA]
        ,[ESTADO]
        ,CONVERT(VARCHAR, [FECHAREGISTROENCABEZADO], 120) AS FECHAREGISTROENCABEZADO
        ,[CANTIDAD]
    FROM [SNVS2].[dbo].[CLINICA]
    WHERE ANIO >= 2018
    """
    
    df = load_sql_data(query)
    
    if df.empty:
        print("Advertencia: No se pudo descargar datos de CLINICA o está vacía.")
        return

    print(f"Datos Monitor Clinica descargados: {len(df)} filas.")
    
    # Optimizaciones básicas
    try:
        df['ANIO'] = df['ANIO'].astype('int16')
        df['SEMANA'] = df['SEMANA'].astype('int8')
        df['CANTIDAD'] = df['CANTIDAD'].fillna(0).astype('int32')
        # Convertir a categoría para ahorrar espacio
        cols_cat = ['PROVINCIA', 'DEPARTAMENTO', 'ESTADO', 'ORIGEN']
        for col in cols_cat:
            if col in df.columns:
                df[col] = df[col].astype('category')
    except Exception as e:
        print(f"Advertencia optimizando tipos Monitor Clinica: {e}")

    output_path = get_data_path('monitor_clinica.parquet')
    print(f"Guardando a {output_path}...")
    
    try:
        df.to_parquet(output_path, engine='pyarrow', compression='snappy')
        print("¡Listo! Archivo monitor_clinica.parquet generado.")
    except Exception as e:
        print(f"Error guardando Monitor Clinica Parquet: {e}")

if __name__ == "__main__":
    export_to_parquet()
    convert_csv_to_parquet()
    export_climahisto()
    export_monitor_clinica()
