# app/db_connection.py

import os
import traceback
import databricks.sql

def run_databricks_query(query: str) -> str:
    """
    Ejecuta un 'query' en Databricks.
    Retorna string con filas o con error.
    """
    print("\n=== run_databricks_query ===")
    print(query)  
    
    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")

    if not host or not token or not http_path:
        return "Error: Faltan DATABRICKS_HOST, DATABRICKS_TOKEN o DATABRICKS_HTTP_PATH."

    try:
        with databricks.sql.connect(
            server_hostname=host,
            http_path=http_path,
            access_token=token,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

                if cursor.description:
                    col_names = [desc[0] for desc in cursor.description]
                else:
                    col_names = []

                res = f"Query: {query}\nColumns: {col_names}\n"
                if rows:
                    for r in rows:
                        res += str(r) + "\n"
                else:
                    res += "(No rows returned)\n"
                return res
    except Exception as exc:
        trace = traceback.format_exc()
        return f"Error al ejecutar query:\n{exc}\n{trace}"

