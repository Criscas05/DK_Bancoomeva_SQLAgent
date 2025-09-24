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
import sys
import openai
from typing import Optional
import logging
import unicodedata
import re
# import fitz  
import pandas as pd
from tqdm import tqdm
from azure.core.exceptions import ResourceNotFoundError
from azure.core.credentials import AzureKeyCredential
from utils.az_open_ai import AzureOpenAIFunctions
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from app import config
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Tuple
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

class AzureIASearch:
        """
        Clase que proporciona funcionalidades para interactuar con Azure AI Search.

        Esta clase permite realizar operaciones como la creación de índices, carga de documentos,
        eliminación de documentos y gestión de identificadores únicos (hashes) en un índice de Azure AI Search.

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
            self.endpoint = config.AZURE_SEARCH_ENDPOINT
            self.api_key = config.AZURE_SEARCH_KEY

            self.endpoint_oai = config.AZURE_OPENAI_ENDPOINT
            self.api_key_oai = config.AZURE_OPENAI_API_KEY
            self.model_name_oai = config.AZURE_OPENAI_MODEL_NAME
            self.api_version_oai = config.AZURE_OPENAI_API_VERSION

            # Cliente para la gestión de índices
            self.index_client = SearchIndexClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.api_key)
            )
        
        @staticmethod
        def normalize_text(text: str) -> str:
            """
            Normaliza un texto para búsqueda o indexación en Azure AI Search.
            
            - Convierte a minúsculas
            - Elimina tildes y diacríticos
            - Quita caracteres especiales y signos de puntuación
            - Reemplaza múltiples espacios por uno solo
            - Elimina espacios iniciales y finales

            Parámetros:
                text (str): Texto a normalizar

            Retorna:
                str: Texto normalizado
            """
            if not isinstance(text, str):
                return ""

            # Convertir a minúsculas
            text = text.lower()

            # Eliminar acentos y diacríticos
            text = unicodedata.normalize('NFD', text)
            text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

            # Eliminar caracteres especiales (mantener letras, números y espacios)
            text = re.sub(r'[^a-z0-9\s]', '', text)

            # Reemplazar múltiples espacios por uno solo
            text = re.sub(r'\s+', ' ', text)

            # Eliminar espacios al inicio y final
            text = text.strip()

            return text

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
        
        def delete_documents_by_ids(self, index_name: str, document_ids: List[str]) -> bool:
            """
            Elimina documentos de un índice especificado basado en una lista de IDs de documentos.
            
            Parámetros:
                index_name (str): Nombre del índice del cual se eliminarán los documentos.
                document_ids (List[str]): Lista de IDs de documentos a eliminar.
            
            Retorna:
                bool: True si se realizó la petición de borrado, False en caso contrario.
            """
            search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=index_name,
                credential=AzureKeyCredential(self.api_key)
            )
            
            documents_to_delete = [{"id": doc_id} for doc_id in document_ids]
            result = search_client.delete_documents(documents=documents_to_delete)
            return True if result else False