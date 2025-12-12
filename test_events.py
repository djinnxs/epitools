import duckdb

path = 'c:/Users/Julio/Documents/dashboard5/data/base_semanal.parquet'
con = duckdb.connect()

# Ver TODOS los eventos distintos (primeros 50)
print("=== TODOS LOS EVENTOS (primeros 50) ===\n")
query1 = f"SELECT DISTINCT NOMBREEVENTOAGRP FROM '{path}' ORDER BY NOMBREEVENTOAGRP LIMIT 50"
eventos = con.execute(query1).df()
for i, evento in enumerate(eventos['NOMBREEVENTOAGRP'], 1):
    print(f"{i:2}. {evento}")

# Ver provincias distintas
print("\n\n=== PROVINCIAS DISPONIBLES ===\n")
query2 = f"SELECT DISTINCT PROVINCIA FROM '{path}' ORDER BY PROVINCIA"
provincias = con.execute(query2).df()
for prov in provincias['PROVINCIA']:
    print(f"  - {prov}")

# Ver años disponibles
print("\n\n=== AÑOS DISPONIBLES ===\n")
query3 = f"SELECT DISTINCT ANIO FROM '{path}' ORDER BY ANIO DESC"
años = con.execute(query3).df()
print(f"  {años['ANIO'].tolist()}")

# Contar registros totales
print("\n\n=== REGISTROS TOTALES ===\n")
query4 = f"SELECT COUNT(*) as total FROM '{path}'"
total = con.execute(query4).df()
print(f"  Total de registros: {total['total'].iloc[0]:,}")

con.close()
