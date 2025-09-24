import sys
sys.path.append('../utils')
from azure.search.documents.indexes.models import (
    SimpleField, VectorSearch, VectorSearchProfile, SemanticConfiguration, SemanticPrioritizedFields,
    HnswAlgorithmConfiguration, SemanticField, SearchFieldDataType, SearchField, ScoringProfile,MagnitudeScoringFunction,
    MagnitudeScoringParameters,ScoringFunctionAggregation,TextWeights,
)

# ----------------------------------------------------------------
# Crear los campos (fields)

def create_fields():

    fields_index = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
        ),
        SearchField(
            name="user_query",
            type=SearchFieldDataType.String,
            searchable=True, 
            filterable=True,
            sortable=False,
            facetable=False,
        ),
        SimpleField(
            name="sql_query",
            type=SearchFieldDataType.String,
            retrievable=True,
            filterable=True
        ),
        SearchField(
            name="embedded_user_query",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="HnswProfile"
        ),
        SimpleField(
            name="catalog",
            type=SearchFieldDataType.String,
            retrievable=True,
            filterable=True
        ),
        SimpleField(
            name="db_schema",
            type=SearchFieldDataType.String,
            retrievable=True,
            filterable=True
        ),
        SimpleField(
            name="table",
            type=SearchFieldDataType.String,
            retrievable=True,
            filterable=True
        )
    ]

    return fields_index

# ----------------------------------------------------------------
# Configuración de búsqueda vectorial
def create_vectorsearch():
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="Hnswconfig",
                kind="hnsw",
                parameters={
                    "metric": "cosine",  # Métrica de distancia (puede ser 'cosine', 'dotProduct', o 'euclidean')
                    "m": 8,  # Número de conexiones bidireccionales por nodo
                    "ef_construction": 400,  # Controla la calidad de la construcción del grafo
                    "efSearch": 500,
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="HnswProfile",
                algorithm_configuration_name="Hnswconfig"
            )
        ]
    )
    
    return vector_search

# ----------------------------------------------------------------
# Configuración semántica para el fields de razones
def create_semantic_config():
    semantic_config = SemanticConfiguration(
                name="semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="user_query")],
                ),
            )
    
    return semantic_config