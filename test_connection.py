# test_connection.py
import os
from dotenv import load_dotenv
import pyodbc

load_dotenv()

print("Cargando variables de .env...")
print(f"Servidor: {os.getenv('SQL_SERVER')}")
print(f"Base: {os.getenv('SQL_DATABASE')}")
print(f"Usuario: {os.getenv('SQL_UID')}")

try:
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_UID')};"
        f"PWD={os.getenv('SQL_PWD')};"
    )
    conn = pyodbc.connect(conn_str)
    print("¡CONEXIÓN EXITOSA!")
    conn.close()
except Exception as e:
    print(f"Error: {e}")