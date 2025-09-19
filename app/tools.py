from app.rtmt import Tool
from app.services import search

search_products_text_tool = Tool(
    name="search_products_text",
    description="Búsqueda híbrida (texto + vector) sobre un índice de productos. Úsalo para responder preguntas sobre productos.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Consulta de búsqueda."},
        },
        "required": ["query"],
        "additionalProperties": False
    },
    func=search.hybrid_search,
)




