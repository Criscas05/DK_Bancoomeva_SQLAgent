import os
import sys
import logging
import pandas as pd
from dotenv import load_dotenv, find_dotenv
import json
import ast

load_dotenv(find_dotenv())

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append('../utils')

from utils.az_open_ai import AzureOpenAIFunctions
from utils.az_ai_search import AzureIASearch
from utils.index_config import create_fields, create_vectorsearch, create_semantic_config

def create_knowledge_base(index_name: str, knowledge_base: pd.DataFrame):

    """
    Crea o actualiza una base de conocimiento en Azure Search para el índice "index_name".

    Parámetros:
        index_name (str): Nombre del índice en Azure Search.
        knowledge_base (pd.DataFrame): DataFrame que contiene la base de conocimiento a cargar.

    Retorna:
        None: La función no retorna ningún valor, pero realiza operaciones de creación/actualización del índice
              y carga de documentos en Azure Search.
    """

    aoi_client = AzureOpenAIFunctions()
    search_client = AzureIASearch()

    # Crear el índice en Azure Search
    fields_index = create_fields()
    vector_search = create_vectorsearch()
    semantic_config = create_semantic_config()

    # Si el índice ya existe, no se eliminará, solo se registrará en log
    search_client.create_index(
        index_name=index_name,
        fields=fields_index,
        vector_search=vector_search,
        semantic_config=[semantic_config],
    )
    # Normalización de la base de conocimientos
    knowledge_base["user_query"] = knowledge_base["user_query"].apply(search_client.normalize_text)

    # Agregar una nueva columna que combine el contenido de todas las columnas
    knowledge_base['columna_para_crear_id'] = knowledge_base.fillna('').astype(str).agg(' '.join, axis=1)

    # Convertir la base de conocimiento en diccionarios antes de generar embeddings
    documents_to_load = knowledge_base.to_dict(orient='records')

    # Asignar hash id a cada documento
    for doc in documents_to_load:
        content = doc.get("columna_para_crear_id", "")
        doc['id'] = search_client.consistent_encode(content)

    # Procesar hashes para determinar qué documentos son nuevos, cuáles omitir y cuáles eliminar
    hashes_ids = [doc["id"] for doc in documents_to_load]
    new_hashes, keep_hashes, delete_hashes = search_client.process_hash_ids(index_name=index_name, hash_ids_list=hashes_ids)

    # Eliminar documentos no presentes en la nueva lista
    if len(delete_hashes) > 0:
        bool_result = search_client.delete_documents_by_ids(index_name=index_name, document_ids=delete_hashes)
        print(f"Documentos eliminados del índice: {bool_result}")

    # Filtrar solo nuevos documentos
    new_docs = [doc for doc in documents_to_load if doc["id"] in new_hashes]

    # Mostrar resultado de la validación del índice
    index_info = {
        "num_added": len(new_docs),
        "num_skipped": len(keep_hashes),
        "num_deleted": len(delete_hashes)
    }
    print(f"Index validation result: \n {index_info}")

    # Generar embeddings solo para los documentos nuevos
    if len(new_docs) > 0:
        new_docs_df = pd.DataFrame(new_docs)
        
        # Generar embeddings para los nuevos documentos
        new_docs_embeddings = aoi_client.embeddings_generation(
            new_docs_df,
            columns={"sql_query": "embedded_user_query"}
        )

        # Subir nuevos documentos al índice (ya con embeddings y tags)
        search_client.upload_documents(new_docs_embeddings, index_name)

        return new_docs_embeddings, index_name
    else:
        print("No hay documentos nuevos para cargar al índice.")

    logging.info("Proceso completado con éxito.")
