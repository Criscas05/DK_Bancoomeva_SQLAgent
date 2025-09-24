from databricks import sql
from databricks.sql.exc import ServerOperationError
from sqlalchemy.util import column_set
from app import config
import json

class DatabricksService:
    """Servicio para ejecutar consultas en un SQL Warehouse de Databricks."""

    def __init__(self):
        """Inicializa los parámetros de conexión."""
        self.hostname = config.DATABRICKS_SERVER_HOSTNAME
        self.http_path = config.DATABRICKS_HTTP_PATH
        self.token = config.DATABRICKS_TOKEN
        print("Servicio de Databricks inicializado.")

    def execute_query(self, query: str):
        """
        Ejecuta una única consulta SQL en Databricks y devuelve las filas y columnas.
        Este método es síncrono y debe ser llamado desde un hilo asíncrono si es necesario.
        """
        print(f"--- Ejecutando consulta en Databricks: {query}... ---")
        try:
            with sql.connect(
                server_hostname=self.hostname,
                http_path=self.http_path,
                access_token=self.token,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    # Devuelve una estructura de datos, no un string JSON
                    return {"columns": columns, "rows": rows}
        except ServerOperationError as e:
            error_message = f"Error de SQL: {e}. Revisa la sintaxis."
            print(error_message)
            # Lanza una excepción para que la herramienta la maneje
            raise ValueError(error_message)
        except Exception as e:
            error_message = f"Error inesperado: {e}"
            print(error_message)
            raise ValueError(error_message)