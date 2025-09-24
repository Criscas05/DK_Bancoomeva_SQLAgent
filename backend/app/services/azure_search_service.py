from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery, QueryType
import re
import unicodedata
from app import config
import json
import sys, os
from typing import List, Dict, Optional
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.az_open_ai import AzureOpenAIFunctions
from utils.az_ai_search import AzureIASearch

class AzureSearchService:
    """Servicio para buscar consultas similares en Azure AI Search."""
    
    def __init__(self):
        """Inicializa el cliente de Azure AI Search."""
        if not all([config.AZURE_SEARCH_ENDPOINT, config.AZURE_SEARCH_KEY, config.AZURE_SEARCH_INDEX_NAME]):
            raise ValueError("Las variables de entorno de Azure AI Search deben estar configuradas.")
        
        self.endpoint = config.AZURE_SEARCH_ENDPOINT
        self.key = config.AZURE_SEARCH_KEY
        
        print("Servicio de Azure AI Search inicializado.")


    async def search_similar_queries(self, user_query: str, top_k: int = 20, index_name: str = "index_sqlagent") -> List[Dict]:
        """
        Busca consultas similares en Azure AI Search usando búsqueda híbrida.
        
        Args:
            user_query: Consulta del usuario en lenguaje natural
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de diccionarios con consultas similares encontradas
        """
        try:
            #Normalizamos la consulta
            ai_search = AzureIASearch()
            user_query = ai_search.normalize_text(user_query)


            print(f"--- Buscando consultas similares para: '{user_query}' ---")

            # Este cliente se usa para buscar documentos en el indice definido por "index_name"
            search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=index_name,
                credential=AzureKeyCredential(self.key)
            )
            # 1. Generar el vector para la consulta del usuario
            openai_client = AzureOpenAIFunctions()
            query_vector = openai_client.get_embedding(user_query)

            # 2. Construir la consulta vectorial
            vector_query = VectorizedQuery(
                vector=query_vector, 
                k_nearest_neighbors=top_k, 
                fields="embedded_user_query" # El campo vectorial en el índice
            )

            print(f"🔍 Realizando búsqueda híbrida para: '{user_query}'")

            # 3. Ejecutar la búsqueda
            search_results = search_client.search(
                search_text=user_query,
                search_fields=["user_query"],  # Campo de texto completo para búsqueda
                vector_queries=[vector_query], # Campo de vectores completo para búsqueda
                # query_type=QueryType.SEMANTIC,  # Activa la reclasificación semántica1
                top=top_k, # Número de resultados a devolver después de la reclasificación
                select=["user_query", "sql_query"], # Seleccionamos los campos a recuperar
            )
            
            similar_queries = []
            for result in search_results:
                # if result['@search.reranker_score'] > 0:
                similar_queries.append({
                    "user_query": result.get("user_query"),
                    "sql_query": result.get("sql_query"),
                    "score": result.get("@search.score", 0),
                    # "reranker_score": result.get("@search.reranker_score", 0)
                })
            similar_queries = similar_queries[:3]
            print(f"--- Encontradas {len(similar_queries)} consultas similares ---")
            return similar_queries
            
        except Exception as e:
            print(f"Error al buscar consultas similares: {e}")
            return []

    def format_context_for_agent(self, similar_queries: List[Dict], table_schema: str) -> str:
        """
        Formatea el contexto para el agente incluyendo esquema y ejemplos.
        
        Args:
            similar_queries: Lista de consultas similares
            table_schema: Esquema de la tabla
            
        Returns:
            Contexto formateado para el agente
        """
        context = f"""
**CONTEXTO DE LA TABLA:**
{table_schema}

**CONSULTAS SIMILARES ENCONTRADAS:**
"""
        
        if similar_queries:
            for i, query in enumerate(similar_queries, 1):
                context += f"""
**Ejemplo {i}** (Similitud: {query.get('score', 0):.2f}):
- Pregunta: "{query.get('user_query')}"
- SQL: {query.get('sql_query')}

"""
        else:
            context += "No se encontraron consultas similares en la base de ejemplos.\n"
        
        context += """
**INSTRUCCIONES:**
- Usa los ejemplos como referencia para construir tu consulta SQL
- Adapta la consulta SQL del ejemplo más similar a la pregunta del usuario
- Si no hay ejemplos similares, construye la consulta basándote en el esquema de la tabla
- Mantén la misma estructura y patrones de los ejemplos cuando sea posible
"""
        
        return context
