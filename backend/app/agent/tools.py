# Aquí definimos las "capacidades" o "habilidades" que el agente puede utilizar.
# La principal será la capacidad de ejecutar una consulta SQL en Databricks.

import json
import re
import uuid
from datetime import date
import pandas as pd
from langchain_core.tools import tool
# from langchain_core.pydantic_v1 import BaseModel, Field
from app.services.databricks_service import DatabricksService
from app.services.azure_search_service import AzureSearchService
from app.services.azure_storage_service import AzureStorageService
from app.services.cosmos_db_service import CosmosDBService # Importamos el servicio de Cosmos
from tenacity import retry, stop_after_attempt, wait_fixed
import asyncio
from app import config

# Instanciamos los servicios una vez para reutilizar la configuración.
databricks_service = DatabricksService()
azure_search_service = AzureSearchService()
cosmos_db_service = CosmosDBService()
storage_service = AzureStorageService()

# Cuántos registros mostraremos al agente si el resultado se trunca.
RESULTS_LIMIT_FOR_THE_AGENT = int(config.RESULTS_LIMIT_FOR_THE_AGENT)


def _sanitize_table_identifier(sql_query: str) -> str:
    """
    Usa regex para encontrar y corregir el formato del identificador de tabla completo.
    Garantiza que el catálogo 'ia-foundation' esté siempre entre comillas invertidas
    y que el resto del identificador no las tenga.
    """
    # Patrón Regex para encontrar el identificador de tres partes:
    # 1. (\`?ia-foundation\`?): Captura 'ia-foundation' con o sin comillas.
    # 2. \s*\.\s*: Coincide con el punto separador, permitiendo espacios.
    # 3. (\`?[\w-]+\`?): Captura el esquema (ej. 'pilotos') con o sin comillas.
    # 4. (\`?[\w-]+\`?): Captura la tabla (ej. 'ods_cliente') con o sin comillas.
    pattern = re.compile(r"(\`?ia-foundation\`?)\s*\.\s*(\`?[\w-]+\`?)\s*\.\s*(\`?[\w-]+\`?)", re.IGNORECASE)

    def replacer(match):
        # Extrae las partes capturadas y les quita las comillas que puedan tener.
        catalog = match.group(1).strip('`')
        schema = match.group(2).strip('`')
        table = match.group(3).strip('`')
        
        # Reconstruye el identificador con el formato correcto y obligatorio.
        return f"`{catalog}`.{schema}.{table}"

    # Busca todas las ocurrencias del patrón en la consulta y las reemplaza.
    return pattern.sub(replacer, sql_query)

@tool
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def execute_databricks_query(sql_query: str, session_id: str, message_id: str) -> str:
    """
    Ejecuta una consulta SQL en Databricks. El 'session_id' y 'message_id' son inyectados
    automáticamente por el sistema. La herramienta SIEMPRE guarda el resultado completo y 
    devuelve solo una muestra al agente.
    """

    if not session_id or not message_id:
        return "Error: session_id y message_id no fueron encontrados en el contexto de la herramienta. La ejecución no puede continuar."

    print(f"--- Herramienta 'execute_databricks_query' llamada para session_id: {session_id}, message_id: {message_id} ---")

    
    query_sanitized = _sanitize_table_identifier(sql_query.strip().strip('`').rstrip(';'))

    try:
        def sync_executor(query):
            return databricks_service.execute_query(query)

        # 1. Ejecutar la consulta para obtener el resultado completo
        full_result_data = await asyncio.to_thread(sync_executor, query_sanitized)

        # 2. Convertir a DataFrame de Pandas
        df = pd.DataFrame(full_result_data["rows"], columns=full_result_data["columns"])
        
        # 3. Subir el CSV COMPLETO a Azure Blob Storage
        blob_name = f"{session_id}-{message_id}.csv"
        download_url = await storage_service.upload_query_results(df, blob_name)
        
        # print("##### Hola pasé upload_query_results")
        # 4. Guardar SIEMPRE una muestra del resultado completo en Cosmos DB
        await cosmos_db_service.save_query_result(session_id, message_id, full_result_data)

        # print("##### Hola pasé save_query_result")

        # 5. Preparar el resumen y la muestra para el LLM
        total_count = len(full_result_data["rows"])
        data_sample = [
            {
                k: (v.isoformat() if isinstance(v, date) else v)
                for k, v in dict(zip(full_result_data["columns"], row)).items()
            }
            for row in full_result_data["rows"][:RESULTS_LIMIT_FOR_THE_AGENT]
        ]

        if total_count <= RESULTS_LIMIT_FOR_THE_AGENT:

            summary_for_agent = {
                "estado": "Resultados de la consulta devueltos completamente, háblale de ellos",
                "resultado_consulta_sql": data_sample,
                "download_url": download_url
            }

        elif total_count > RESULTS_LIMIT_FOR_THE_AGENT and total_count <= 100:

            summary_for_agent = {
                "estado": f"La consulta devolvió un total de {total_count} registros, háblale de estos primeros 10. En la tabla inferior del front el usuario puede observarlos completamente. Recuerdale que el también puede descargarlos.",
                "resultado_consulta_sql": data_sample,
                "download_url": download_url
            }

        elif total_count > 100:

            summary_for_agent = {
                "estado": f"La consulta devolvió un total de {total_count} registros, háblale de estos primeros 10. En la tabla inferior del front el usuario puede observar una muestra mayor. Para visualizarlos todos, puede descargar el CSV con los resultados",
                "resultado_consulta_sql": data_sample,
                "download_url": download_url
            }

        # print(f"0000000 ---/ SUMARY RESULTS EXECUTE DATABRICKS --> {summary_for_agent}")
        return json.dumps(summary_for_agent, indent=2, default=str)

    except (ValueError, Exception) as e:
        return str(e)

@tool
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_database_schema_info(table_name: str = None) -> str:
    """
    Proporciona información sobre el esquema de la base de datos.
    Si no se proporciona 'table_name' (None), devuelve una lista de todas las tablas disponibles.
    Si se proporciona 'table_name', devuelve el esquema detallado (nombres de columnas, tipos) de esa tabla específica.
    Usa esta herramienta si no estás seguro sobre los nombres de las columnas.
    """
    # Limpiamos el nombre de la tabla por si el LLM lo pasa con comillas
    clean_table_name = table_name.strip('`') if table_name else "`ia-foundation`.pilotos.ods_cliente"

    if table_name:
        # Pide la descripción detallada de una tabla específica
        # query = f"DESCRIBE TABLE {table_name};"
        query = "DESCRIBE TABLE `ia-foundation`.pilotos.ods_cliente"
        prompt = f"Obteniendo el esquema para la tabla '{table_name}'..."
    else:
        # Pide la lista de todas las tablas en el esquema especificado
        # IMPORTANTE: Ajusta `ia-foundation`.`pilotos` al catálogo y esquema que estés usando.
        query = "SHOW TABLES IN `ia-foundation`.`pilotos`;"
        prompt = "Obteniendo la lista de todas las tablas disponibles..."

    print(f"--- Herramienta 'get_database_schema_info' llamada: {prompt} ---")
    
    # Reutilizamos nuestro servicio de Databricks para ejecutar esta consulta
    print(f"query para Databricks: {query}")
    # Formateamos la salida para que sea más útil para el LLM
    try:
        def sync_schema_executor(q):
            return databricks_service.execute_query(query=q)
            
        result_data = await asyncio.to_thread(sync_schema_executor, query)
        data = [dict(zip(result_data["columns"], row)) for row in result_data["rows"]]

        # Extraemos solo la información relevante para no saturar el prompt
        if table_name:

            # --- Formateo a Tabla Markdown ---
        
            # Encabezado de la tabla
            header = "| Columna | Tipo de Dato | Descripción |\n|---|---|---|"

            # Construir cada fila de la tabla
            rows = []
            for col in data:
                # Limpiamos los comentarios para que no rompan el formato de la tabla
                col_name = col.get('col_name', 'N/A')
                data_type = col.get('data_type', 'N/A')
                comment = col.get('comment', 'N/A') or 'N/A' # Asegurarse de que no sea None
                cleaned_comment = comment.replace('\n', ' ').replace('|', '') # Quitar saltos de línea y pipes
                
                rows.append(f"| {col_name} | {data_type} | {cleaned_comment} |")
            
            # Unir todo en un solo string
            formatted_info = f"Esquema para la tabla `{clean_table_name}`:\n\n{header}\n" + "\n".join(rows)

            print("--- Esquema de tabla formateado exitosamente como Markdown para el agente. ---")

        else:
            # Para SHOW TABLES, extraemos solo los nombres de las tablas
            formatted_info = "Available tables: " + ", ".join([tbl['tableName'] for tbl in data])
        
        print("--- Esquema de tabla formateado exitosamente para el agente. ---")
        return formatted_info
    except (ValueError, Exception) as e:
        error_msg = f"No se pudo obtener el esquema de la tabla: {str(e)}"
        print(f"--- ERROR en get_database_schema_info: {error_msg} ---")
        return error_msg

# --- HERRAMIENTA: EL "MAPA" ESTRUCTURAL ---
@tool
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_table_structural_summary(table_name: str = "`ia-foundation`.pilotos.ods_cliente") -> str:
    """
    Proporciona un resumen ESTRUCTURAL y CONCISO del esquema de la tabla. Devuelve
    el nombre de la columna, su tipo de dato y una BREVE descripción.
    Usa esta herramienta primero para entender la estructura general de la tabla.
    NO devuelve la lista de valores posibles de cada columna.
    """
    query = f"DESCRIBE TABLE {table_name}"
    print(f"--- Herramienta 'get_table_structural_summary' llamada para: {table_name} ---")
    
    try:
        def sync_executor(q):
            return databricks_service.execute_query(query=q)
            
        result_data = await asyncio.to_thread(sync_executor, query)
        data = [dict(zip(result_data["columns"], row)) for row in result_data["rows"]]
        
        header = "| Columna | Tipo de Dato | Descripción Breve |\n|---|---|---|"
        rows = []
        for col in data:
            comment = col.get('comment', '') or ''
            # --- LÓGICA CLAVE: Extraemos solo la primera línea del comentario ---
            # Esto nos da la descripción sin la lista masiva de valores.
            brief_description = comment.split('\n')[0].strip()
            rows.append(f"| {col.get('col_name', 'N/A')} | {col.get('data_type', 'N/A')} | {brief_description} |")
        
        formatted_info = f"Resumen estructural para la tabla `{table_name}`:\n\n{header}\n" + "\n".join(rows)
        return formatted_info

    except Exception as e:
        return f"No se pudo obtener el resumen estructural de la tabla: {str(e)}"

# --- HERRAMIENTA: EL "ZOOM" SEMÁNTICO ---
@tool
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_column_value_map(column_name: str, descriptive_column_name: str, table_name: str = "`ia-foundation`.pilotos.ods_cliente") -> str:
    """
    Devuelve los valores únicos y sus descripciones para una columna categórica específica.
    Usa esta herramienta DESPUÉS de ver el resumen estructural, si necesitas mapear un
    valor del usuario (ej. 'Oficina Chipichape') a un código en la base de datos (ej. 108).
    Args:
        column_name (str): El nombre de la columna de códigos (ej. 'AGEHOMO').
        descriptive_column_name (str): El nombre de la columna con la descripción (ej. 'STRAGEHOMO').
    """
    query = f"SELECT DISTINCT {column_name}, {descriptive_column_name} FROM {table_name} ORDER BY {column_name} ASC"
    print(f"--- Herramienta 'get_column_value_map' llamada para la columna: {column_name} ---")
    
    try:
        def sync_executor(q):
            return databricks_service.execute_query(query=q)
            
        result_data = await asyncio.to_thread(sync_executor, query)
        
        # Formateamos como una tabla Markdown para máxima claridad
        header = f"| Columna ({column_name}) | Descripción ({descriptive_column_name}) |\n|---|---|"
        rows = [f"| {row[0]} | {row[1]} |" for row in result_data["rows"]]
        
        formatted_info = f"Mapeo de valores para la columna `{column_name}`:\n\n{header}\n" + "\n".join(rows)
        return formatted_info
        
    except Exception as e:
        return f"No se pudo obtener el mapeo de valores para la columna {column_name}: {str(e)}"

@tool
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def search_similar_queries(user_query: str) -> str:
    """
    Busca consultas similares en la base de ejemplos usando Azure AI Search.
    Esta herramienta encuentra consultas SQL de ejemplo que son similares a la pregunta del usuario.
    Úsala para obtener contexto y ejemplos de consultas SQL que puedas adaptar.
    Esto te ayudará a construir la consulta correcta más rápidamente.
    
    Args:
        user_query: La consulta del usuario en lenguaje natural
        
    Returns:
        Contexto formateado con ejemplos de consultas similares
    """
    print(f"--- Herramienta 'search_similar_queries' llamada con: {user_query} ---")
    
    try:
        # Buscar consultas similares
        similar_queries = await azure_search_service.search_similar_queries(user_query, top_k=10)
        
        if not similar_queries:
            return "No se encontraron consultas similares en la base de ejemplos. Procederé a construir la consulta basándome únicamente en el esquema de la tabla."
        
        # Formatear el contexto para el agente
        context = "**CONSULTAS SIMILARES ENCONTRADAS:**\n\n"
        
        for i, query in enumerate(similar_queries, 1):
            context += f"**Ejemplo {i}**:\n"
            context += f"- Pregunta: \"{query.get('user_query')}\"\n"
            context += f"- SQL: {query.get('sql_query')}\n\n"
        
        context += "**INSTRUCCIONES:**\n"
        context += "- Usa estos ejemplos similares como referencia para construir tu consulta SQL\n"
        context += "- Mantén la misma estructura y patrones de los ejemplos cuando sea posible\n"
        
        print(f"--- Contexto generado con {len(similar_queries)} ejemplos similares ---")
        return context
        
    except Exception as e:
        print(f"Error al buscar consultas similares: {e}")
        return f"Error al buscar consultas similares: {e}"

# Lista de herramientas para ser usadas por el agente
agent_tools = [execute_databricks_query, get_table_structural_summary, get_column_value_map, search_similar_queries]