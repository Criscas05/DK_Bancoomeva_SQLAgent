# app/azure_search.py

import os
import logging
from typing import Optional, List
import hashlib
import numpy as np
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchField,
    SearchableField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch
)
from langchain_openai import AzureOpenAIEmbeddings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AzureSearchService:
    """
    Servicio para crear/actualizar un índice en Azure Cognitive Search
    y realizar (1) upsert de documentos con embeddings,
    y (2) búsqueda vectorial.
    """

    def __init__(self, index_name: str = "agent-sql-index-v2"):
        self.index_name = index_name

        # Cargar credenciales de .env
        self.endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
        self.key = os.getenv("AZURE_AI_SEARCH_API_KEY")
        if not self.endpoint or not self.key:
            raise ValueError("Faltan AZURE_AI_SEARCH_ENDPOINT o AZURE_AI_SEARCH_API_KEY en .env")

        self.credential = AzureKeyCredential(self.key)

        self.embedding_model = AzureOpenAIEmbeddings(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("EMBEDDING_NAME")
        )

    async def create_or_update_index(self):
        """
        Crea o actualiza un índice con:
          - id
          - question
          - sql_query
          - catalog
          - db_schema
          - content_vector
        """
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="question", type=SearchFieldDataType.String),
            SearchableField(name="sql_query", type=SearchFieldDataType.String),
            SearchableField(name="catalog", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="db_schema", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="myHnswProfile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw"
                )
            ],
        )

        semantic_config = SemanticConfiguration(
            name="agent-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="question"),
                keywords_fields=[SemanticField(field_name="question")],
                content_fields=[SemanticField(field_name="question")]
            ),
        )
        semantic_search = SemanticSearch(configurations=[semantic_config])

        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )

        async with SearchIndexClient(endpoint=self.endpoint, credential=self.credential) as index_client:
            result = await index_client.create_or_update_index(index)
            logger.info(f"Índice {result.name} creado/actualizado.")

    async def upsert_document(
        self,
        question: str,
        sql_query: str,
        catalog: str,
        db_schema: str,
        doc_id: Optional[str] = None
    ):
        """
        Genera embedding y sube un documento con:
         - question
         - sql_query
         - catalog
         - db_schema
         - content_vector (embedding)
         - id (generado con un hash si no se provee)

        ***En este caso, generamos el ID usando solo la question***
        => así si el usuario edita la SQL para la misma question,
           se hace “update” en Azure Search (machacando la versión previa).
        """
        text_for_embedding = question.strip()
        embedding = self.embedding_model.embed_query(text_for_embedding)

        if not doc_id:
            # Enfasis: ID se basa SOLO en question => un doc por “pregunta”
            raw_hash = hashlib.md5(question.strip().encode("utf-8")).hexdigest()
            doc_id = f"q-{raw_hash}"

        doc = {
            "id": doc_id,
            "question": question,
            "sql_query": sql_query,
            "catalog": catalog,
            "db_schema": db_schema,
            "content_vector": embedding
        }

        async with SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential) as sc:
            result = await sc.upload_documents([doc])
            logger.info(f"Upserted doc with id={doc_id} => {result}")

    async def search_vector(
        self,
        query_text: str,
        top_k: int = 3
    ) -> List[dict]:
        """
        Búsqueda vectorial (preview).
        Genera embedding, hace un Vector(value=embedding, k=top_k, fields="content_vector").
        """
        embedding = self.embedding_model.embed_query(query_text.strip())

        async with SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential) as sc:
            results = await sc.search(
                search_text=None,
                vector_queries=[{
                    "kind": "vector",
                    "vector": embedding,
                    "k": top_k,
                    "fields": "content_vector"
                }],
                select=["id","question","sql_query","catalog","db_schema"]
            )
            out = []
            async for r in results:
                doc = {
                    "id": r["id"],
                    "question": r["question"],
                    "sql_query": r["sql_query"],
                    "catalog": r["catalog"],
                    "db_schema": r["db_schema"],
                    "score": r["@search.score"]
                }
                out.append(doc)
            return out

    async def search_textual(
        self,
        text: str,
        top_k: int = 3
    ) -> List[dict]:
        """
        Búsqueda textual 'clásica' (no vector).
        """
        async with SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential) as sc:
            results = await sc.search(
                search_text=text,
                top=top_k,
                select=["id","question","sql_query","catalog","db_schema"]
            )
            out = []
            async for r in results:
                doc = {
                    "id": r["id"],
                    "question": r["question"],
                    "sql_query": r["sql_query"],
                    "catalog": r["catalog"],
                    "db_schema": r["db_schema"],
                    "score": r["@search.score"]
                }
                out.append(doc)
            return out

    async def search_hybrid(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[dict]:
        """
        Búsqueda *híbrida* (texto + vector) con reranking semántico.
        - `search_text`  →  recupera candidatos por BM25 / semantic ranker.
        - `vector_queries` →  re‑ordena usando similitud de embeddings.
        - Azure fusiona ambos rankings con Reciprocal‑Rank‑Fusion (RRF).

        Devuelve una lista de dicts: id, question, sql_query,
        catalog, db_schema, score.
        """
        # 1. Generamos embedding SOLO de la pregunta
        embedding = self.embedding_model.embed_query(query_text.strip())

        async with SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
            api_version="2025-03-01-preview"
        ) as sc:
            print("\n--- HYBRID DEBUG ---")
            print("Consulta:", query_text)
            results = await sc.search(
                search_text=query_text,                           
                vector_queries=[{                                
                    "kind": "vector",
                    "vector": embedding,
                    "k": 50,
                    "fields": "content_vector"
                }],
                query_type="simple",  
                query_language="es",                     
                semantic_configuration_name="agent-semantic-config",
                top=50,
                select=["id", "question", "sql_query",
                        "catalog", "db_schema"],
                debug = "all"   
            )

            out: List[dict] = []
            async for r in results:
                dbg = r.get("@search.document_debug_info")
                vec_score = None
                if dbg:
                    try:
                        vec_score = dbg.vectors.subscores.text.search_score
                    except AttributeError:
                        pass           # por si el SDK cambia

                out.append({
                    "id":            r["id"],
                    "question":      r["question"],
                    "sql_query":     r["sql_query"],
                    "catalog":       r["catalog"],
                    "db_schema":     r["db_schema"],
                    # ‘semanticScore’ te da 1-4   (ranker)
                    "semanticScore": r.get("@search.reranker_score"),
                    # ‘vectorScore’ te da 0-80    (similitud cruda)
                    "vectorScore":   vec_score,
                    # ‘finalScore’   te da 0-0.1  (RRF normalizado)
                    "finalScore":    r["@search.score"],
                })
                
            return out
