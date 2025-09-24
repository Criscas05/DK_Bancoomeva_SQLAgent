from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import uuid
import os
import sys

# notebook_dir = os.getcwd()
# parent_dir = os.path.abspath(os.path.join(notebook_dir, '..'))
# sys.path.append(parent_dir)

# Importar los servicios, esquemas y el agente real
from app.services.cosmos_db_service import CosmosDBService
from app.services.azure_storage_service import AzureStorageService
from app.schemas import ChatRequest, ChatResponse, QueryResultSample
from app.agent.graph import agent_executor
# from app.agent import agent_executor, execute_databracks_query
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from fastapi import HTTPException, Path
from app import config

# --- Inicialización de servicios y constantes ---
cosmos_service = CosmosDBService()
storage_service = AzureStorageService()
CONVERSATION_HISTORY_WINDOW = int(config.CONVERSATION_HISTORY_WINDOW)

def _sanitize_history_for_api(history: list) -> list:
    """
    Elimina cualquier 'ToolMessage' huérfano del principio del historial
    para asegurar una secuencia de conversación válida para la API de OpenAI.
    """
    sanitized_history = list(history)
    # Mientras el historial no esté vacío y el primer mensaje sea un ToolMessage...
    while sanitized_history and isinstance(sanitized_history[0], ToolMessage):
        # Lo eliminamos, porque su AIMessage correspondiente fue cortado por la ventana.
        sanitized_history.pop(0)
    return sanitized_history

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona las tareas de inicio y apagado."""
    print("--- La aplicación está iniciando ---")
    await cosmos_service.initialize_resources()
    # Asegurar contenedor de Azure Storage
    try:
        await storage_service.initialize_container()
    except Exception as e:
        # No detenemos el arranque, pero registramos el error para diagnosticar
        print(f"Error inicializando contenedor de Storage: {e}")
    print("--- Inicialización de recursos de Cosmos DB completada ---")
    yield
    print("--- La aplicación se está apagando ---")


app = FastAPI(
    title="SQL Agent API",
    description="API para interactuar con un Agente SQL usando LangGraph y Azure.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", tags=["Health Check"])
def read_root():
    """Endpoint raíz para verificar que la API está funcionando."""
    return {"status": "ok", "message": "Welcome to the SQL Agent API"}


@app.post("/chat", response_model=ChatResponse, tags=["Agent"])
async def chat_with_agent(request: ChatRequest):

    user_query = request.user_query
    corrected_sql_query = request.corrected_sql_query
    session_id = request.session_id or str(uuid.uuid4())
    message_id = request.message_id or str(uuid.uuid4())
    
    try:
        # Recuperamos el historial de la base de datos para tener contexto.
        conversation_history = await cosmos_service.get_conversation_history(
            session_id,
            limit=CONVERSATION_HISTORY_WINDOW
        )
        # --- Sanitización del Historial ---
        # Nos aseguramos de que el historial no comience con un ToolMessage huérfano.
        sanitized_history = _sanitize_history_for_api(conversation_history)

        messages_for_agent = list(sanitized_history)

        if corrected_sql_query:

            # --- RUTA 1: VÍA RÁPIDA DE CORRECCIÓN DE SQL ---
            print(f"--- Vía Rápida: Ejecutando SQL corregido por el usuario ---")

            # Creamos un HumanMessage que instruye al agente a llamar a la herramienta.
            correction_message = HumanMessage(
                content=f"He corregido la consulta anterior. Por favor, ejecuta esta nueva versión:\n\n```sql\n{corrected_sql_query}\n```"
            )

            # Creamos un AIMessage "falso" que instruye al agente a llamar a la herramienta.
            pre_fabricated_tool_call = {
                "name": "execute_databricks_query",
                "args": {
                    "sql_query": corrected_sql_query,
                    "message_id": message_id,
                    "session_id": session_id
                    },
                "id": f"{str(uuid.uuid4())}"
            }
            ai_message_with_tool_call = AIMessage(
                content="",
                tool_calls=[pre_fabricated_tool_call]
            )
            # Añadimos estos mensajes fabricados al historial que pasaremos al agente.
            messages_for_agent.extend([correction_message, ai_message_with_tool_call])

        else:

            # --- RUTA 2: FLUJO NORMAL DEL AGENTE ---
            print(f"--- Flujo Normal: Invocando al agente ---")

            # Añadimos el mensaje del usuario.
            current_user_message = HumanMessage(content=user_query)
            messages_for_agent.append(current_user_message)

        # Invocar al agente con el fabricado o el estado preparado con la serialización de mensajes
        initial_state = {
            "messages": messages_for_agent,
            "session_id": session_id,
            "message_id": message_id,
            "sql_query": corrected_sql_query or "",
            "sql_results_download_url": ""
        }
        agent_response = await agent_executor.ainvoke(initial_state)

        # Guardar el historial completo del turno en la DB.
        new_messages_from_turn = agent_response.get("messages", [])[len(sanitized_history):]

        # Guardar el "proceso de pensamiento" completo en la DB.
        await cosmos_service.add_messages(session_id, new_messages_from_turn)

        # Preparar y devolver la respuesta final al usuario.
        final_response_content = new_messages_from_turn[-1].content if new_messages_from_turn else "No se generó una respuesta."

        # Extraemos el SQL y la URL del estado final del grafo.
        sql_query = agent_response.get("sql_query")
        sql_results_download_url = agent_response.get("sql_results_download_url")

        return ChatResponse(
            response=final_response_content,
            sql_query=sql_query,
            session_id=session_id,
            message_id=message_id,
            sql_results_download_url=sql_results_download_url
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")

@app.get("/get_sample_result/{session_id}/{message_id}")
async def get_large_result(
    session_id: str = Path(..., description="ID de la sesión donde se guardó el resultado"),
    message_id: str = Path(..., description="ID del mensaje asociado al resultado")):
    """
    Endpoint para que el frontend descargue una muestra de los resultados completos de una consulta
    que fueron guardados en Cosmos DB.
    """
    try:
        result_doc = await cosmos_service.get_query_result(session_id, message_id)
        if not result_doc:
            return {"error": "Resultado no encontrado. Verifique los identificadores."}

        result_data = result_doc['data']
        
        return QueryResultSample(columns=result_data["columns"], rows=result_data['rows'])

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ocurrió un error inesperado: {e}")