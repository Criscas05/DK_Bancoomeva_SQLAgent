from app.rtmt import Tool

FIXED_INDEX_NAME = "magenta-sand-46qlhmn39w"  # índice fijo
DEFAULT_SELECT = ["content", "title"]

from app.services import embedder , search

async def get_weather(args: dict):
    location = args["location"]
    data = {
        "current": {
            "temperatureC": 20,
            "weather": "Sunny",
        }
    }
    result = f"Current temperature in {location} is {data['current']['temperatureC']}°C and the weather is {data['current']['weather']}."
    return result

weather_tool = Tool(
    name="get_weather",
    description="Get current temperature for provided coordinates in Celsius.",
    parameters={
        "type": "object",
        "properties": { "location": { "type": "string" } },
        "required": ["location"],
        "additionalProperties": False
    },
    func=get_weather,
)

async def show_map(args: dict):
    return args["map_id"]

show_map_tool = Tool(
    name="show_map",
    description="Devuelve el identificador del mapa para una ubicación dada, o la palabra |limpiar| para borrar el mapa actual.",
    parameters={
        "type": "object",
        "properties": { 
            "map_id": { 
                "type": "string", 
                "enum": [
                    "ia",
                    "banos",
                    "salon360",
                    "ciberseguridad",
                    "conectividad",
                    "showroom",
                    "cafeteria",
                    "limpiar",
                ]
            }
        },
        "required": ["map_id"],
        "additionalProperties": False
    },
    func=show_map,
)

async def azure_hybrid_search_func(args: dict):
    query = args["query"]
    k = args.get("k", 5)

    hits = await search.hybrid_search(
        query=query,
        index_name=FIXED_INDEX_NAME,
        k=k,
        select=DEFAULT_SELECT
    )

    shaped = []
    for h in hits:
        item = {
            "id": h.get("id"),
            "score": h.get("@search.score"),
            "reranker_score": h.get("@search.reranker_score"),
        }
        # Captions/answers si existen
        if h.get("@search.captions"):
            try:
                item["caption"] = h["@search.captions"][0].get("text")
            except Exception:
                pass
        if h.get("@search.answers"):
            try:
                item["answer"] = h["@search.answers"][0].get("text")
            except Exception:
                pass

        # Campos seleccionados por defecto
        item["fields"] = {f: h.get(f) for f in DEFAULT_SELECT if f in h}
        shaped.append(item)

    return {"count": len(shaped), "items": shaped}

azure_hybrid_search_tool = Tool(
    name="azure_hybrid_search",
    description="Búsqueda híbrida (texto + vector) sobre un índice fijo de Azure Cognitive Search. Devuelve id, score, caption y campos básicos.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Consulta de búsqueda."},
            "k": {"type": "integer", "description": "Número de resultados (default=5)."}
        },
        "required": ["query"],
        "additionalProperties": False
    },
    func=azure_hybrid_search_func,
)




