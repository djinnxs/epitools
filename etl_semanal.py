import pandas as pd
import os
from utils.common import load_sql_data

def export_to_parquet():
    """Descarga la tabla principal DashClinica2 de SQL y la guarda como base_semanal.parquet"""
    print("\nIniciando descarga de SQL (Tabla DashClinica2)...")
    
    query = """
    SELECT 
        [CODIGO_PROVINCIA], [PROVINCIA], [COD_DEPTO], [DEPARTAMENTO], [LOCALIDAD],
        [ANIO], [SEMANA], [NOMBREEVENTOAGRP], [ID_SNVS_EVENTO_AGRP],
        [IDEDAD], [GRUPO], [CANTIDAD],
        CONVERT(VARCHAR, [FECHAREGISTROCLINICA], 120) AS FECHAREGISTROCLINICA
    FROM [SNVS2].[dbo].[DashClinica2]
    WHERE ANIO >= 2018
    """
    
    df = load_sql_data(query)
    
    if df.empty:
        print("Error: No se obtuvieron datos de SQL. Verifique conexión y tabla.")
        return

    print(f"Datos descargados con éxito: {len(df)} filas.")
    
    # Normalización de textos para evitar duplicados por acentos o mayúsculas
    def normalize_str(s):
        if pd.isna(s): return s
        import unicodedata
        s = str(s).strip().upper()
        # Eliminar acentos
        s = ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')
        return s

    if 'DEPARTAMENTO' in df.columns:
        df['DEPARTAMENTO'] = df['DEPARTAMENTO'].apply(normalize_str)
    if 'LOCALIDAD' in df.columns:
        df['LOCALIDAD'] = df['LOCALIDAD'].apply(normalize_str)
    if 'NOMBREEVENTOAGRP' in df.columns:
        df['NOMBREEVENTOAGRP'] = df['NOMBREEVENTOAGRP'].apply(normalize_str)

    # Optimizaciones de tipos de datos para reducir tamaño y aumentar velocidad
    try:
        df['ANIO'] = df['ANIO'].astype('int16')
        df['SEMANA'] = df['SEMANA'].astype('int8')
        df['CANTIDAD'] = df['CANTIDAD'].fillna(0).astype('int32')
        df['ID_SNVS_EVENTO_AGRP'] = df['ID_SNVS_EVENTO_AGRP'].fillna(0).astype('int32')
        df['IDEDAD'] = df['IDEDAD'].fillna(0).astype('int16')
        
        # Categorías para ahorrar memoria y velocidad
        cols_cat = ['PROVINCIA', 'CODIGO_PROVINCIA', 'DEPARTAMENTO', 'COD_DEPTO', 'LOCALIDAD',
                    'NOMBREEVENTOAGRP', 'GRUPO']
        for col in cols_cat:
            if col in df.columns:
                df[col] = df[col].astype('category')
    except Exception as e:
        print(f"Nota: No se pudo optimizar tipos, se guardará como objeto: {e}")

    output_path = os.path.join('data', 'base_semanal.parquet')
    print(f"Guardando en {output_path}...")
    
    try:
        df.to_parquet(output_path, engine='pyarrow', compression='snappy')
        print("¡Operación completada! base_semanal.parquet actualizado.")
    except Exception as e:
        print(f"Error al guardar el archivo Parquet: {e}")


def export_monitor_clinica():
    """Descarga la tabla CLINICA de SQL y la guarda como monitor_clinica.parquet"""
    print("\nIniciando descarga de SQL (Monitor Clinica - Tabla CLINICA)...")
    
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
    
    # Normalización de textos para evitar duplicados por acentos o mayúsculas
    def normalize_str(s):
        if pd.isna(s): return s
        import unicodedata
        s = str(s).strip().upper()
        # Eliminar acentos
        s = ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')
        return s

    if 'DEPARTAMENTO' in df.columns:
        df['DEPARTAMENTO'] = df['DEPARTAMENTO'].apply(normalize_str)

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

    output_path = os.path.join('data', 'monitor_clinica.parquet')
    print(f"Guardando a {output_path}...")
    
    try:
        df.to_parquet(output_path, engine='pyarrow', compression='snappy')
        print("¡Listo! Archivo monitor_clinica.parquet generado.")
    except Exception as e:
        print(f"Error guardando Monitor Clinica Parquet: {e}")


# =====================================================================
# BLOQUE DE EJECUCIÓN ÚNICA
# =====================================================================
if __name__ == "__main__":
    export_to_parquet()       # 1. Trae DashClinica2 -> base_semanal.parquet
    export_monitor_clinica()   # 2. Trae CLINICA       -> monitor_clinica.parquet
    
    print("\n[OK] ETL finalizado. Solo se procesaron los 2 archivos requeridos.")