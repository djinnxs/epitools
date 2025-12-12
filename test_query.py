import duckdb
from utils.query_builder import NaturalLanguageQueryBuilder

path = 'c:/Users/Julio/Documents/dashboard5/data/base_semanal.parquet'

# Crear query builder
qb = NaturalLanguageQueryBuilder()

# Probar consulta "diarrea en jujuy 2023"
print("=== PRUEBA: diarrea en jujuy 2023 ===\n")
df, params = qb.execute_query("diarrea en jujuy 2023", path)

print(f"Provincias detectadas: {params['provincias']}")
print(f"Eventos detectados: {params['eventos']}")
print(f"Años detectados: {params['años']}")
print(f"\n{params['message']}\n")

if not df.empty:
    print("RESULTADOS:")
    print(df)
    print(f"\nTotal cantidad: {df['CANTIDAD'].sum():,.0f}")
else:
    print("No se encontraron resultados")
    
print("\n\nSQL Generado:")
print(params.get('sql_query', 'N/A'))
