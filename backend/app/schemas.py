from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Este archivo centraliza los modelos de datos para validar
# las peticiones y respuestas de la API, asegurando consistencia.

class ChatRequest(BaseModel):
    """Modelo para la petición del endpoint /chat."""
    user_query: str = Field(..., description="La consulta en lenguaje natural del usuario.", min_length=1)
    session_id: str | None = Field(default=None, description="ID de sesión para mantener el contexto. Si es nulo, se creará uno nuevo.")
    message_id: str = Field(..., description="ID del mensaje, para tener control de cada pregunta hecha por el usuario")
    corrected_sql_query: Optional[str] = Field(default=None, description="Consulta SQL opcionalmente corregida por el usuario.")

class ChatResponse(BaseModel):
    """Modelo para la respuesta del endpoint /chat."""
    response: str = Field(..., description="La respuesta generada por el agente.")
    sql_query: str = Field(..., description="Query SQL utilizada por el agente.")
    session_id: str = Field(..., description="El ID de sesión de la conversación actual.")
    message_id: str = Field(..., description="ID del mensaje, identificador unico del mensaje y usado para guardar respuesta sql en cosmos db")
    sql_results_download_url: Optional[str] = None

class QueryResultSample(BaseModel):
    columns: List[str] = Field(..., description="Lista de nombres de columnas")
    rows: List[Dict[str, Any]] = Field(..., description="Primeras filas de la consulta (máx 100)")


