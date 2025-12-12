# utils/query_builder.py
import re
import pandas as pd
from typing import Dict, List, Optional, Tuple
import streamlit as st

class NaturalLanguageQueryBuilder:
    """
    Sistema basado en reglas para convertir consultas en lenguaje natural a SQL.
    Sin dependencias externas, usa regex y diccionarios.
    """
    
    def __init__(self):
        # Diccionario de provincias (nombre normalizado -> nombre EXACTO en base de datos)
        # Los nombres en la base están en Title Case: "Salta", "Buenos Aires", etc.
        self.provincias = {
            'jujuy': 'Jujuy',
            'salta': 'Salta',
            'formosa': 'Formosa',
            'chaco': 'Chaco',
            'misiones': 'Misiones',
            'corrientes': 'Corrientes',
            'santiago del estero': 'Santiago del Estero',
            'tucuman': 'Tucumán',
            'tucumán': 'Tucumán',
            'catamarca': 'Catamarca',
            'la rioja': 'La Rioja',
            'san juan': 'San Juan',
            'san luis': 'San Luis',
            'mendoza': 'Mendoza',
            'cordoba': 'Córdoba',
            'córdoba': 'Córdoba',
            'santa fe': 'Santa Fe',
            'entre rios': 'Entre Ríos',
            'entre ríos': 'Entre Ríos',
            'buenos aires': 'Buenos Aires',
            'caba': 'CABA',
            'ciudad autonoma de buenos aires': 'CABA',
            'ciudad autónoma de buenos aires': 'CABA',
            'CAPITAL FEDERAL': 'CABA',
            'capital federal': 'CABA',
            'la pampa': 'La Pampa',
            'neuquen': 'Neuquén',
            'neuquén': 'Neuquén',
            'rio negro': 'Río Negro',
            'río negro': 'Río Negro',
            'chubut': 'Chubut',
            'santa cruz': 'Santa Cruz',
            'tierra del fuego': 'Tierra del Fuego',
        }
        
        # Palabras clave para eventos de salud (basado en NOMBREEVENTOAGRP de la base de datos)
        # Formato: término_búsqueda -> término_parcial_para_búsqueda_en_base
        # Usamos búsqueda parcial para ser más flexibles
        self.eventos_keywords = {
            # Bronquiolitis - variaciones comunes
            'bronquiolitis': 'Bronquiolitis en menores de 2 años (sin especificar)',
            'bronquilitis': 'Bronquiolitis en menores de 2 años (sin especificar)',
            'bronquioliti': 'Bronquiolitis en menores de 2 años (sin especificar)',
            'bronquiliti': 'Bronquiolitis en menores de 2 años (sin especificar)',
            'bronco': 'Bronquiolitis en menores de 2 años (sin especificar)',
            
            # Diarreas - singular y plural
            'diarrea': 'Diarreas',
            'diarreas': 'Diarreas',
            
            # Enfermedad tipo influenza (ETI)
            'influenza': 'Enfermedad tipo influenza (ETI)',
            'gripe': 'Enfermedad tipo influenza (ETI)',
            'eti': 'Enfermedad tipo influenza (ETI)',
            'ETI': 'Enfermedad tipo influenza (ETI)',
            'enfermedad tipo influenza': 'Enfermedad tipo influenza (ETI)',
            
            # IRAG - Infección respiratoria aguda grave
            'irag': 'IRAG - Infección respiratoria aguda grave',
            'IRAG': 'IRAG - Infección respiratoria aguda grave',
            'infeccion respiratoria': 'IRAG - Infección respiratoria aguda grave',
            'infección respiratoria': 'IRAG - Infección respiratoria aguda grave',
            'respiratoria aguda': 'IRAG - Infección respiratoria aguda grave',
            
            # Neumonía
            'neumonia': 'Neumonía (sin especificar)',
            'neumonía': 'Neumonía (sin especificar)',
            'pulmonia': 'Neumonía (sin especificar)',
            
            # Otros eventos que pueden agregarse en el futuro
            'dengue': 'DENGUE',
            'covid': 'COVID',
            'coronavirus': 'COVID',
            'sarampion': 'SARAMPION',
            'sarampión': 'SARAMPION',
            'varicela': 'VARICELA',
            'tos convulsa': 'TOS CONVULSA',
            'meningitis': 'MENINGITIS',
            'tuberculosis': 'TUBERCULOSIS',
            'chagas': 'CHAGAS',
            'fiebre amarilla': 'FIEBRE AMARILLA',
            'zika': 'ZIKA',
            'chikungunya': 'CHIKUNGUNYA',
            'leptospirosis': 'LEPTOSPIROSIS',
            'hantavirus': 'HANTAVIRUS',
            'rabia': 'RABIA',
        }
        
        # Regiones agregadas (usando nombres exactos de la base)
        self.regiones = {
            'norte': ['Jujuy', 'Salta', 'Formosa', 'Chaco', 'Misiones', 'Corrientes'],
            'noroeste': ['Jujuy', 'Santiago del Estero', 'Salta', 'Tucumán', 'Catamarca', 'La Rioja'],
            'NOA': ['Jujuy', 'Santiago del Estero', 'Salta', 'Tucumán', 'Catamarca', 'La Rioja'],
            'noa': ['Jujuy', 'Santiago del Estero', 'Salta', 'Tucumán', 'Catamarca', 'La Rioja'],
            'noreste': ['Formosa', 'Chaco', 'Misiones', 'Corrientes'],
            'NEA': ['Formosa', 'Chaco', 'Misiones', 'Corrientes'],
            'nea': ['Formosa', 'Chaco', 'Misiones', 'Corrientes'],
            'cuyo': ['Mendoza', 'San Juan', 'San Luis'],
            'CUYO': ['Mendoza', 'San Juan', 'San Luis'],
            'centro': ['Córdoba', 'Santa Fe', 'Entre Ríos', 'Buenos Aires', 'CABA'],
            'CENTRO': ['Córdoba', 'Santa Fe', 'Entre Ríos', 'Buenos Aires', 'CABA'],
            'SUR': ['Neuquén', 'Río Negro', 'Chubut', 'Santa Cruz', 'La Pampa', 'Tierra del Fuego'],
            'sur': ['Neuquén', 'Río Negro', 'Chubut', 'Santa Cruz', 'La Pampa', 'Tierra del Fuego'],
        }
    
    def parse_query(self, query_text: str) -> Dict:
        """
        Analiza la consulta en lenguaje natural y extrae parámetros.
        
        Returns:
            Dict con keys: provincias, eventos, años, departamentos, accion
        """
        query_lower = query_text.lower()
        
        result = {
            'provincias': [],
            'eventos': [],
            'años': [],
            'departamentos': [],
            'regiones': [],
            'accion': 'tabla',  # por defecto
            'success': True,
            'message': ''
        }
        
        # Detectar provincias
        for keyword, provincia in self.provincias.items():
            if keyword in query_lower:
                if provincia not in result['provincias']:
                    result['provincias'].append(provincia)
        
        #  Detectar regiones
        for region, provincias in self.regiones.items():
            if region in query_lower:
                result['regiones'].append(region)
                result['provincias'].extend([p for p in provincias if p not in result['provincias']])
        
        # Detectar eventos
        for keyword, evento in self.eventos_keywords.items():
            if keyword in query_lower:
                if evento not in result['eventos']:
                    result['eventos'].append(evento)
        
        # Detectar años (números de 4 dígitos entre 2000-2040)
        años_match = re.findall(r'\b(20[0-4][0-9])\b', query_text)
        if años_match:
            result['años'] = sorted([int(año) for año in set(años_match)])
        
        # Detectar rangos de años (ej: "entre 2020 y 2022", "desde 2019 hasta 2021")
        rango_match = re.search(r'(?:entre|desde)\s+(\d{4})\s+(?:y|hasta|a)\s+(\d{4})', query_lower)
        if rango_match:
            año_inicio = int(rango_match.group(1))
            año_fin = int(rango_match.group(2))
            result['años'] = list(range(año_inicio, año_fin + 1))
        
        # Detectar acción solicitada
        if any(word in query_lower for word in ['grafico', 'gráfico', 'graficá', 'graficar', 'visualizar', 'mostrar grafico']):
            result['accion'] = 'grafico'
        elif any(word in query_lower for word in ['total', 'suma', 'cantidad total', 'cuanto', 'cuánto']):
            result['accion'] = 'total'
        
        # Validar que se haya detectado algo
        if not result['provincias'] and not result['eventos'] and not result['años']:
            result['success'] = False
            result['message'] = '⚠️ No pude detectar provincias, eventos o años en tu consulta. Intenta ser más específico.'
        
        return result
    
    def build_duckdb_query(self, params: Dict, parquet_path: str) -> str:
        """
        Construye una consulta DuckDB basada en los parámetros extraídos.
        Incluye agrupamiento y suma como en las otras páginas.
        """
        # Query base con agrupamiento
        query = f"""
        SELECT 
            PROVINCIA,
            ANIO,
            NOMBREEVENTOAGRP,
            SUM(CANTIDAD) as CANTIDAD
        FROM '{parquet_path}'
        WHERE 1=1
        """
        
        # Agregar filtros
        if params.get('provincias'):
            provincias_str = "', '".join(params['provincias'])
            query += f"\n    AND PROVINCIA IN ('{provincias_str}')"
        
        if params.get('eventos'):
            # Usar UPPER() con LIKE para coincidencias case-insensitive
            eventos_conditions = []
            for evento in params['eventos']:
                # Convertir ambos a mayúsculas para comparación case-insensitive
                eventos_conditions.append(f"UPPER(NOMBREEVENTOAGRP) LIKE UPPER('%{evento}%')")
            query += f"\n    AND ({' OR '.join(eventos_conditions)})"
        
        if params.get('años'):
            años_str = ', '.join(map(str, params['años']))
            query += f"\n    AND ANIO IN ({años_str})"
        
        # Agrupamiento
        query += """
        GROUP BY PROVINCIA, ANIO, NOMBREEVENTOAGRP
        ORDER BY ANIO DESC, PROVINCIA, NOMBREEVENTOAGRP
        """
        
        return query
    
    def execute_query(self, query_text: str, parquet_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Ejecuta la consulta completa: parsea, construye SQL y ejecuta.
        
        Returns:
            Tuple[DataFrame con resultados, Dict con parámetros detectados]
        """
        import duckdb
        
        # Parsear la consulta
        params = self.parse_query(query_text)
        
        if not params['success']:
            return pd.DataFrame(), params
        
        try:
            # Construir query SQL
            sql_query = self.build_duckdb_query(params, parquet_path)
            
            # Ejecutar con DuckDB
            with duckdb.connect() as con:
                df = con.execute(sql_query).df()
            
            params['sql_query'] = sql_query
            params['message'] = f"✅ Encontrados {len(df)} registros"
            
            return df, params
            
        except Exception as e:
            params['success'] = False
            params['message'] = f'❌ Error al ejecutar consulta: {str(e)}'
            return pd.DataFrame(), params
    
    def get_available_values(self, parquet_path: str) -> Dict:
        """
        Obtiene los valores únicos disponibles en el Parquet para ayudar al usuario.
        """
        import duckdb
        
        try:
            with duckdb.connect() as con:
                # Obtener eventos únicos
                eventos = con.execute(f"SELECT DISTINCT NOMBREEVENTOAGRP FROM '{parquet_path}' ORDER BY NOMBREEVENTOAGRP").df()
                # Obtener años únicos
                años = con.execute(f"SELECT DISTINCT ANIO FROM '{parquet_path}' ORDER BY ANIO DESC").df()
                # Obtener provincias únicas
                provincias = con.execute(f"SELECT DISTINCT PROVINCIA FROM '{parquet_path}' ORDER BY PROVINCIA").df()
                
                return {
                    'eventos': eventos['NOMBREEVENTOAGRP'].tolist(),
                    'años': años['ANIO'].tolist(),
                    'provincias': provincias['PROVINCIA'].tolist()
                }
        except Exception as e:
            st.error(f"Error al obtener valores: {e}")
            return {'eventos': [], 'años': [], 'provincias': []}
