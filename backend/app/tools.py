# app/tools.py

import os
from app.db_connection import run_databricks_query
from langchain_core.tools import tool
from app.azure_search import AzureSearchService

def sql_db_list_tables(input: str, catalog: str, schema: str) -> str:
    """
    Muestra todas las tablas del schema sin truncar.
    """
    query = f"SHOW TABLES IN {catalog}.{schema}"
    
    raw_result = run_databricks_query(query)

    lines = raw_result.split("\n")
    table_names = []
    for line in lines:
        if line.startswith("(") and ",'" in line:
            parts = line.split(",")
            if len(parts) >= 2:
                tname = parts[1].strip().strip("'")
                table_names.append(tname)
    
    if not table_names:
        return raw_result
    
    return "Tablas disponibles:\n" + "\n".join(f"- {t}" for t in table_names)

def sql_db_schema(table_name: str, catalog: str, schema: str) -> str:
    """
    Describe la tabla dada en Databricks (catalog.schema.table).
    """
    full_name = f"{catalog}.{schema}.{table_name}"
    #full_name = f"{table_name}"
    query = f"DESCRIBE EXTENDED {full_name}"
    print("Query:", query)
    return run_databricks_query(query)

def db_query_tool(query: str) -> str:
    """
    Ejecuta un query arbitrario en Databricks.
    """
    return run_databricks_query(query)


@tool(description="Busca en el índice de Azure Search una consulta SQL similar para la pregunta dada, filtrando por catalog y schema.")
async def search_stored_query_tool(query: str, catalog: str, db_schema: str) -> str:
    """
    Usa el servicio AzureSearchService para buscar en el índice "agent-sql-index-v2"
    un documento cuya 'question' sea similar al 'query' proporcionado y que
    tenga el mismo catalog y db_schema. Si el mejor documento supera cierto
    threshold de similitud, devuelve un JSON con { 'sql_query': '...', 'score': ... }.
    En caso de no encontrar nada relevante, retorna un string indicando que no hay coincidencias.
    """
    try:
        azure_svc = AzureSearchService(index_name="agent-sql-index-v2")
        # Búsqueda vectorial
        results = await azure_svc.search_hybrid(query_text=query, top_k=5)
        
        # Filtramos solo coincidencias que tengan el mismo catalog y db_schema
        same_schema_docs = [r for r in results if r["catalog"] == catalog and r["db_schema"] == db_schema]
        if not same_schema_docs:
            return "NO_MATCH: No se encontró ninguna consulta guardada para este schema/catalog."
        
        same_schema_docs.sort(
            key=lambda d: -(d.get("vectorScore", -1))
        )

        best_doc = same_schema_docs[0]
        print(f"best_doc: {best_doc}")
        # second_doc = same_schema_docs[1]
        # print("🟡 second_best_doc:", second_doc)

        if len(same_schema_docs) > 1:
            second_doc = same_schema_docs[1]
            print("🟡 second_best_doc:", second_doc)
        else:
            print("ℹ️ Solo se encontró un resultado coincidente en Azure Search.")

        return (
            "MATCH_FOUND: "
            f"original_question={best_doc['question']}, "
            f"sql_query={best_doc['sql_query']}, "
            f"score={best_doc['vectorScore']}"
        )

    except Exception as ex:
        return f"ERROR_SEARCH: {str(ex)}"