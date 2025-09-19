import logging
from typing import Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from langchain_openai import AzureOpenAIEmbeddings

from app import config

# ── Clases ──────────────────────────────────────────────────────────────────────
class AzureOpenAI:
    def __init__(self):
        self.embeddings_model: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
            azure_deployment=config.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            openai_api_version=config.AZURE_OPENAI_API_VERSION,
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            openai_api_key=config.AZURE_OPENAI_API_KEY,
        )

azure_openai = AzureOpenAI()

class AzureAISearch:
    def __init__(
        self,
        embeddings_model: Optional[Any] = None,
        vector_field: str = "embedding",
        semantic_config_name: str = "my-semantic-config",
    ):
        self.embeddings_model = embeddings_model
        self.vector_field = vector_field
        self.semantic_config_name = semantic_config_name
        self.search_client: SearchClient = SearchClient(
            endpoint=config.AZURE_SEARCH_ENDPOINT,
            index_name=config.AZURE_SEARCH_INDEX,
            credential=AzureKeyCredential(config.AZURE_SEARCH_KEY),
        )

    async def hybrid_search(self, args: dict) -> str:
        query = args["query"]
        k = args.get("k", 3)

        try:
            query_embedding = self.embeddings_model.embed_query(query)
            results = await self.search_client.search(
                search_text=query,
                vector_queries=[{
                    "kind": "vector",
                    "vector": query_embedding,
                    "fields": self.vector_field,
                    "k": k,
                }],
                query_type="semantic",
                semantic_configuration_name=self.semantic_config_name,
                top=k,
            )

            chunks = []
            async for r in results:
                chunks.append(r["content"].strip())

            return "\n\n".join(chunks)

        except Exception as e:
            logging.exception(f"Error en búsqueda híbrida: {str(e)}")
            return "Error en búsqueda híbrida"

search = AzureAISearch(embeddings_model=azure_openai.embeddings_model)