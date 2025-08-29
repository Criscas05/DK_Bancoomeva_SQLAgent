from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchFieldDataType, SearchField, SemanticSearch
)
from azure.search.documents.models import (
    QueryType,
    VectorizedQuery,
    VectorQuery,
)

import os
import openai
from typing import Optional
import logging
# import fitz  
import pandas as pd
from tqdm import tqdm
from azure.core.exceptions import ResourceNotFoundError
from azure.core.credentials import AzureKeyCredential
import hashlib
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Tuple
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

class AzureIASearch:
        """
        Clase que proporciona funcionalidades para interactuar con Azure AI Search.

        Esta clase permite realizar operaciones como la creación de índices, carga de documentos,
        búsquedas híbridas, eliminación de documentos y gestión de identificadores únicos (hashes)
        en un índice de Azure AI Search.

        Atributos:
            endpoint (str): Punto de conexión para Azure AI Search.
            api_key (str): Clave de API para autenticación en Azure AI Search.
            endpoint_oai (str): Punto de conexión para Azure OpenAI.
            api_key_oai (str): Clave de API para autenticación en Azure OpenAI.
            model_name_oai (str): Nombre del modelo de embeddings en Azure OpenAI.
            api_version_oai (str): Versión de la API de Azure OpenAI.
            index_client (SearchIndexClient): Cliente para la gestión de índices en Azure AI Search.
        """
        def __init__(self):
            """
            Inicializa la clase AzureSearchFunctions con las credenciales y configuración necesarias.

            Carga las credenciales y configuraciones desde variables de entorno y configura el cliente
            para la gestión de índices en Azure AI Search.
            """
            # Load credentials from secret manager or environment variables
            self.endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
            self.api_key = os.getenv("AZURE_AI_SEARCH_API_KEY")

            self.endpoint_oai = os.getenv("AZURE_OPENAI_ENDPOINT")
            self.api_key_oai = os.getenv("AZURE_OPENAI_API_KEY")
            self.model_name_oai = os.getenv("EMBEDDING_NAME")
            self.api_version_oai = os.getenv("AZURE_OPENAI_API_VERSION")

            # Cliente para la gestión de índices
            self.index_client = SearchIndexClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )

        def consistent_encode(self, input_string: str) -> str:
            """
            Codifica una cadena de manera consistente usando SHA-256.
            
            Parámetros:
                input_string (str): La cadena a codificar.
            
            Retorna:
                encoded (str): La cadena codificada.
            """
            encoded = hashlib.sha256(input_string.encode()).hexdigest()
            return encoded

        def create_index(self, index_name: str, fields: List[SearchField], vector_search=None, semantic_config=None) -> SearchIndex:
            """
            Crea un índice en Azure Search con opciones avanzadas.
            
            Parámetros:
            - index_name: Nombre del índice.
            - fields: Lista de campos para definir la estructura del índice.
            - vector_search: Configuración opcional para búsqueda vectorial.
            - semantic_config: Configuración opcional para semántica.

            Retorna:
                SearchIndex: El índice creado o actualizado. Retorna None si ocurre un error.

            """
            try:
                existing_indexes = [index.name for index in self.index_client.list_indexes()]
                if index_name in existing_indexes:
                    # Si el índice ya existe, registramos un log y no lo eliminamos.
                    print('----------------------------------------------------------------')
                    print(f"El índice '{index_name}' ya existe. No se creará un nuevo índice.")
                    print('----------------------------------------------------------------')
                    return None

                # Crear el índice ya que no existe
                print('----------------------------------------------------------------')
                print(f"Creando el índice '{index_name}'...")
                semantic_search = SemanticSearch(configurations=semantic_config)
                index = SearchIndex(
                    name=index_name,
                    fields=fields,
                    vector_search=vector_search,
                    semantic_search=semantic_search
                )

                result = self.index_client.create_or_update_index(index)
                print('----------------------------------------------------------------')
                print(f"Índice '{index_name}' creado exitosamente.")
                return result
            except Exception as e:
                print(f"Error creando el índice '{index_name}': {str(e)}")
                return None

        # def upload_documents(self, documents: list[dict], index_name: str) -> None:
        #     """
        #     Carga documentos en Azure Search en batches de máximo 950 documentos por petición.
            
        #     Parámetros:
        #         documents (pd.DataFrame): DataFrame de Pandas con los documentos a cargar.
        #         index_name (str): Nombre del índice donde se cargarán los documentos.
            
        #     Retorna:
        #         None: La función no retorna ningún valor, pero carga los documentos en el índice.
        #     """
        #     # Este cliente se usa para cargar documentos al indice definido por "index_name"
        #     self.search_client_upload = SearchClient(
        #         endpoint=self.endpoint,
        #         index_name=index_name,
        #         credential=AzureKeyCredential(self.api_key)
        #     )
        #     batch_size = 200
        #     total_docs = len(documents)
        #     print(f"Subiendo {total_docs} documentos al índice {index_name} (batch size={batch_size})")
            
        #     for i in range(0, total_docs, batch_size):
        #         batch = documents[i:i+batch_size]
        #         print(f"Subiendo documentos {i+1} a {i+len(batch)}...")
        #         try:
        #             _indexing_results = self.search_client_upload.upload_documents(documents=batch)
        #         except Exception as e:
        #             print(f"Error al subir documentos {i+1} a {i+len(batch)}: {str(e)}")

        def upload_documents(self, documents: pd.DataFrame, index_name: str) -> None:
            """
            Carga documentos en Azure Search. Útil si la longitud del DataFrame es menor a 10000.
            
            Parámetros:
                documents (pd.DataFrame): DataFrame de Pandas con los documentos a cargar.
                index_name (str): Nombre del índice donde se cargarán los documentos.
            
            Retorna:
                None: La función no retorna ningún valor, pero carga los documentos en el índice.
            """
            # Este cliente se usa para cargar documentos al indice definido por "index_name"
            self.search_client_upload = SearchClient(
                endpoint=self.endpoint,
                index_name=index_name,
                credential=AzureKeyCredential(self.api_key)
            )
            print(f"Subiendo {len(documents)} documentos al índice {index_name}")
            try:
                documents = documents.to_dict(orient='records')
                # Asignar hash a cada documento
                for doc in documents:
                    content = doc.get("columna_para_crear_id", "")
                    doc['id'] = self.consistent_encode(content)
                
                # Eliminar la columna auxiliar que se usó para crear el ID
                for doc in documents:
                    doc.pop('columna_para_crear_id', None)

                _indexing_results = self.search_client_upload.upload_documents(documents=documents)

                print('----------------------------------------------------------------')
                print("Documentos subidos correctamente.")
            except Exception as e:
                logging.error(f"Error subiendo los documentos al índice: {str(e)}")
                return None

        def get_all_document_ids(self, index_name: str) -> List[str]:
            """
            Recupera todos los IDs de documentos del índice especificado.
            
            Parámetros:
                index_name (str): Nombre del índice a consultar.
            
            Retorna:
                List[str]: Lista de IDs de documentos.
            """
            # Re-iniciar el cliente de búsqueda con el índice especificado
            search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=index_name,
                credential=AzureKeyCredential(self.api_key)
            )
            
            document_ids = []
            
            # Realizar la búsqueda para recuperar todos los documentos (solo IDs)
            results = search_client.search(
                search_text="*",  
                select="id",    
                top=1000        
            )
            
            for result in results:
                document_ids.append(result["id"])
            
            return document_ids

        def process_hash_ids(self, index_name: str, hash_ids_list: List[str]) -> Tuple[List[str], List[str], List[str]]:
            """
            Procesa una lista de hash_ids y los compara con los registros existentes en el índice.
            
            Parámetros:
                index_name (str): Nombre del índice a consultar.
                hash_ids_list (List[str]): Lista de hash_ids a procesar.
            
            Retorna:
                Tuple[List[str], List[str], List[str]]:
                - new_hash_ids: Hash_ids que no están en el índice (nuevos registros).
                - already_existing_hash_ids: Hash_ids que ya están en el índice.
                - missing_hash_ids: Hash_ids en el índice pero no en la lista de entrada.
            """
            input_hash_ids = set(hash_ids_list)
            existing_hash_ids = set(self.get_all_document_ids(index_name))

            new_hash_ids = list(input_hash_ids - existing_hash_ids)
            already_existing_hash_ids = list(input_hash_ids & existing_hash_ids)
            missing_hash_ids = list(existing_hash_ids - input_hash_ids)

            return new_hash_ids, already_existing_hash_ids, missing_hash_ids
        
        # def hybrid_search(self, query: str, index_name: str, top_k: int = 5, odata_filter:Optional[str] = None) -> list[dict]:
        #     """
        #     Realiza una búsqueda híbrida (vector + texto) con reclasificación semántica.

        #     Args:
        #         query (str): La consulta del usuario.
        #         search_client (SearchClient): El cliente de Azure AI Search.
        #         openai_client (openai.AzureOpenAI): El cliente de Azure OpenAI.
        #         top_k (int): Número de resultados a devolver.

        #     Returns:
        #         list[str]: Una lista de los fragmentos de contenido más relevantes.
        #     """
        #     # Este cliente se usa para buscar documentos en el indice definido por "index_name"
        #     search_client = SearchClient(
        #         endpoint=self.endpoint,
        #         index_name=index_name,
        #         credential=AzureKeyCredential(self.api_key)
        #     )
        #     # 1. Generar el vector para la consulta del usuario
        #     openai_client = AzureServices.AzureOpenAI()
        #     query_vector = openai_client.get_embedding(query)

        #     # 2. Construir la consulta vectorial
        #     vector_query = VectorizedQuery(
        #         vector=query_vector, 
        #         k_nearest_neighbors=top_k, 
        #         fields="embedded_content_ltks" # El campo vectorial en el índice
        #     )

        #     print(f"🔍 Realizando búsqueda híbrida para: '{query}'")

        #     # 3. Ejecutar la búsqueda
        #     results = search_client.search(
        #         search_text=query,
        #         filter=odata_filter,
        #         vector_queries=[vector_query],
        #         query_type=QueryType.SEMANTIC,  # Activa la reclasificación semántica
        #         semantic_configuration_name='semantic-config', # configuración semantica instanciada en AI Search
        #         top=top_k, # Número de resultados a devolver después de la reclasificación
        #         select=["doc_id", "content", "page_number", "bloque", "docnm"], # Seleccionamos los campos de recuperar
        #         highlight_fields="content" # Resaltar los fragmentos de texto relevantes
        #     )

        #     # 4. Recopilar y devolver el contenido de los resultados
        #     #top_content = [content for content in results if content['@search.reranker_score'] > 2]  # Filtro de confianza
        #     top_content = [content for content in results]

        #     if not top_content:
        #         print("⚠️ No se encontraron resultados con un puntaje de reclasificación suficientemente alto.")
        #         return []
                
        #     print(f"📚 Se encontraron {len(top_content)} fragmentos de texto relevantes.")
        #     return top_content