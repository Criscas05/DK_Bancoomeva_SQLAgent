from azure.cosmos import exceptions, PartitionKey, CosmosClient

import logging
import os
from datetime import datetime
from typing import Optional
import uuid
import json

# # ── Variables de entorno obligatorias ──────────────────────────────────────────
# COSMOS_ENDPOINT = os.getenv('COSMOS_ENDPOINT')
# COSMOS_KEY = os.getenv('COSMOS_KEY')
# COSMOS_DATABASE_NAME = os.getenv('COSMOS_DATABASE_NAME')

# # ── Clase CosmosDBClient ──────────────────────────────────────────────────────
# class CosmosDBClient:
#     def __init__(self):
#         """
#             Inicializa la conexión a Azure Cosmos DB.
            
#             :param endpoint: URL del endpoint de Cosmos DB.
#             :param key: Clave de autenticación para Cosmos DB.
#             :param database_name: Nombre de la base de datos a utilizar.
#             :param container_name: Nombre del contenedor a utilizar.
#         """
#         endpoint: str = COSMOS_ENDPOINT
#         key: str = COSMOS_KEY
#         database_name: str = COSMOS_DATABASE_NAME
#         container_registration_name: str = 'registro'
#         container_users_name: str = 'users'

#         try:
#             client = CosmosClient(endpoint, key)
#         except Exception as e:
#             logging.error(f"Error al inicializar CosmosClient: {e}")
#             raise
#         try:
#             database = client.create_database_if_not_exists(id=database_name)
#         except exceptions.CosmosHttpResponseError as e:
#             logging.error(f"Error al crear la base de datos: {e}")
#             raise
#         try:
#             self.container_registration = database.create_container_if_not_exists(
#                 id=container_registration_name,
#                 partition_key=PartitionKey(path="/id")
#             )
#             self.container_user = database.create_container_if_not_exists(
#                 id=container_users_name,
#                 partition_key=PartitionKey(path="/id")
#             )
#         except exceptions.CosmosHttpResponseError as e:
#             logging.error(f"Error al crear los contenedores: {e}")
#             raise
#         print("Conexión a Cosmos DB establecida correctamente.")
#         logging.info("Conexión a Cosmos DB establecida correctamente.")

#     async def save_registration(self, args: dict) -> Optional[dict]:
#         """
#             Guarda un registro en la base de datos de Cosmos DB.
            
#             :param name: Nombre del registro.
#             :param email: Correo electrónico del usuario.
#             :param company_user: Compañía del usuario.
#             :param description: Descripción del registro.
#             :param is_new_user: Indica si el usuario es nuevo o no.

#             :return: El documento creado en Cosmos DB o None si hubo un error.
#         """
#         name = args["name"]
#         email = args["email"]
#         company_user = args["company_user"]
#         description = args["description"]
#         is_new_user = args.get("is_new_user", False)
#         try:
#             if is_new_user:
#                 item_user = {
#                     "id": email,
#                     "name": name,
#                     "company_user": company_user,
#                     "created_at": datetime.now().isoformat()
#                 }
#                 response = self.container_user.create_item(item_user)
#                 logging.info(f"Usuario guardado: {response}")

#             item_registration = {
#                 "id": uuid.uuid4().hex,
#                 "email_user": email,
#                 "description": description,
#                 "date": datetime.now().isoformat()
#             }
#             response = self.container_registration.create_item(item_registration)
#             logging.info(f"Registro guardado: {response}")
#             return response
#         except exceptions.CosmosHttpResponseError as e:
#             logging.error(f"Error al guardar el registro: {e}")
#             return None
        
#     async def get_user(self, args: dict) -> Optional[str]:
#         """
#             Obtiene un usuario de la base de datos de Cosmos DB.
            
#             :param id_user: ID del usuario.

#             :return: El documento del usuario o None si no se encuentra.
#         """
#         email_user = args["email_user"]
#         error_message = "El usuario no esta registrado"
#         try:
#             user = self.container_user.read_item(item=email_user, partition_key=email_user)
#             return json.dumps(user, indent=4, default=str)
#         except exceptions.CosmosResourceNotFoundError:
#             return error_message
#         except exceptions.CosmosHttpResponseError as e:
#             logging.error(f"Error al obtener el usuario: {e}")
#             return error_message

# cosmosdb = CosmosDBClient()


import logging
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import (
    QueryType,
    QueryCaptionType,
    QueryAnswerType,
    VectorizedQuery,
)

class AzureAISearch:
    """
    Búsqueda híbrida (texto + vector). Si proporcionas semantic_config_name,
    usa SEMANTIC; de lo contrario, usa el query simple por defecto.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        *,
        embedding_function: Optional[Any] = None,
        vector_field: str = "content_vector",
        semantic_config_name: Optional[str] = None,
    ):
        self.search_endpoint = endpoint
        self.search_credential = AzureKeyCredential(api_key)
        self.embedding_function = embedding_function
        self.vector_field = vector_field
        self.semantic_config_name = semantic_config_name

    async def hybrid_search(
        self,
        query: str,
        index_name: str,
        *,
        filter_str: Optional[str] = None,
        k: int = 5,
        select: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            if not query:
                logging.error("La consulta no puede estar vacía")
                return []

            vector_query = None
            if self.embedding_function:
                embedding = self.embedding_function.embed_query(query)
                vector_query = VectorizedQuery(
                    vector=embedding,
                    k_nearest_neighbors=k,
                    fields=self.vector_field,
                )

            async with SearchClient(
                endpoint=self.search_endpoint,
                index_name=index_name,
                credential=self.search_credential,
            ) as search_client:
                kwargs = {
                    "search_text": query,
                    "vector_queries": [vector_query] if vector_query else None,
                    "filter": filter_str,
                    "top": k,
                }
                if select:
                    kwargs["select"] = select

                # Solo activar SEMANTIC si realmente existe el nombre
                if self.semantic_config_name:
                    kwargs.update(
                        dict(
                            query_type=QueryType.SEMANTIC,
                            semantic_configuration_name=self.semantic_config_name,
                            query_caption=QueryCaptionType.EXTRACTIVE,
                            query_answer=QueryAnswerType.EXTRACTIVE,
                        )
                    )

                results = await search_client.search(**kwargs)

                hits: List[Dict[str, Any]] = []
                async for r in results:
                    hits.append(dict(r))
                return hits

        except Exception as e:
            logging.exception(f"Error en búsqueda híbrida: {str(e)}")
            return []

def shape(doc, fields=None):
    out = {
        "id": doc.get("id"),
        "score": doc.get("@search.score"),
        "rerankerScore": doc.get("@search.rerankerScore"),
    }
    if doc.get("@search.captions"):
        out["caption"] = doc["@search.captions"][0].get("text")
    if doc.get("@search.answers"):
        out["answer"] = doc["@search.answers"][0].get("text")
    if fields:
        out["fields"] = {f: doc.get(f) for f in fields}
    return out


from openai import AzureOpenAI

class AzureOpenAIEmbeddings:
    def __init__(self, endpoint, api_key, deployment_name):
        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2023-05-15"
        )
        self.deployment = deployment_name

    def embed_query(self, text: str):
        resp = self.client.embeddings.create(
            model=self.deployment,
            input=text
        )
        return resp.data[0].embedding  # list[float] de 1536 elementos

embedder = AzureOpenAIEmbeddings(
    endpoint="https://oai-general.openai.azure.com/",
    api_key="F95F4KJut2ku0kYGn54ZgTeH5nBaJWo7quHnD8748VT8DLx0xHHEJQQJ99BGACHYHv6XJ3w3AAABACOGfNvD",
    deployment_name="text-embedding-ada-002"  # nombre de tu deployment
)

search = AzureAISearch(
    endpoint="https://service-se.search.windows.net",
    api_key="IZFL3I5MIPtajkRY5WyFX8ELQkrcbtwq8rwaXHOUeRAzSeCVLLbG",
    embedding_function=embedder,
    semantic_config_name="azureml-default",
    vector_field="contentVector"
)
