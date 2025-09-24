from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated, Sequence
import operator
import json
from app import config
from app.agent.prompts import SYSTEM_PROMPT
# IMPORTANTE: Importamos TODAS las herramientas.
from app.agent.tools import agent_tools
from app.utils.az_open_ai import AzureOpenAIFunctions

# --- 1. Definir el Estado del Agente ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    message_id: str
    sql_query: str
    sql_results_download_url: str

# --- 2. Definir los Nodos y Herramientas ---

tool_node = ToolNode(agent_tools)
openai_cliente = AzureOpenAIFunctions()
# Atamos el conjunto completo de herramientas al modelo.
model = openai_cliente.llm_4o.bind_tools(agent_tools)

def call_model(state: AgentState):
    print("--- NODO: LLAMANDO AL MODELO ---")

    # Estrategia para almacenar la URL de descarga del resultado completo obtenido por la consulta SQL
    sql_results_download_url = state["sql_results_download_url"]
    last_message = state["messages"][-1]
    if isinstance(last_message,ToolMessage) and last_message.name == "execute_databricks_query":
        try:
            # print(f"####> LAST MESSAGE {last_message}")
            content_dict = json.loads(last_message.content)
            sql_results_download_url = content_dict.get("download_url", sql_results_download_url) # Extraemos la url de descarga para llevarla al state
            # Limpiamos el mensaje para que el LLM no vea la URL.
            content_dict.pop("download_url", None)
            state['messages'][-1].content = json.dumps(content_dict, indent=2, ensure_ascii=False) # Actualizamos la ToolMessage eliminando el campo de "download_url"

        except (json.JSONDecodeError, AttributeError):
            # Si falla (porque es un string de error), simplemente lo ignoramos y continuamos.
            # El agente verá el error en el ToolMessage y podrá reaccionar.
            print("--- El contenido del ToolMessage no es un JSON procesable (probablemente un error), omitiendo extracción de URL. ---")

    messages = state['messages']
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages_with_system = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
    else:
        messages_with_system = messages
    
    response = [model.invoke(messages_with_system)]
    print(f"---------- > State en el momento call model: {state}")

    print("--- Response Model ---")
    print(f"*************** Respuesta Modelo dentro de call model: {response}")
    print("--- Response Model ---")

    # Estrategia para almacenar la QUERY SQL usada por el modelo para responder a la solicitud del usuario
    sql_query = state['sql_query']
    tool_calls = response[0].tool_calls
    if tool_calls and tool_calls[0]["name"] == "execute_databricks_query":
        sql_query = tool_calls[0]["args"]["sql_query"]

    return {**state,
        "messages": response,
        "session_id": state['session_id'],
        "message_id": state['message_id'],
        "sql_query": sql_query,
        "sql_results_download_url": sql_results_download_url
        }

def should_continue(state: AgentState):
    print("--- ARISTA: DECIDIENDO RUTA ---")
    last_message = state['messages'][-1]
    if not last_message.tool_calls:
        print("--- RUTA: A END ---")
        return "end"
    else:
        print("--- RUTA: A HERRAMIENTA ---")

        if last_message.tool_calls[0]["name"] == "execute_databricks_query":
            # print(f"########TOOOOOL CALL execute_databricks_query ->  {last_message.tool_calls}")
            last_message.tool_calls[0]["args"]["session_id"] = state.get("session_id", [])
            last_message.tool_calls[0]["args"]["message_id"] = state.get("message_id", [])
            # print(f"########TOOOOOL CALL execute_databricks_query AJUSTADA->  {last_message.tool_calls}")

        return "continue"

# --- Punto de Entrada Condicional ---
def entry_point_router(state: AgentState):
    """
    Este nodo decide a dónde ir al principio del grafo.
    Si el último mensaje es una llamada a herramienta pre-fabricada, va directo a la acción.
    De lo contrario, va al agente para que piense.
    """
    print("--- NODO DE ENTRADA: Decidiendo ruta inicial ---")
    last_message = state['messages'][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print("--- RUTA INICIAL: A HERRAMIENTA (Vía Rápida) ---")
        return "action"
    else:
        print("--- RUTA INICIAL: A AGENTE (Flujo Normal) ---")
        return "agent"

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.set_conditional_entry_point(
    entry_point_router,
    {"agent": "agent", "action": "action"}
)
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "action", "end": END},
)
workflow.add_edge("action", "agent")

try:
    agent_executor = workflow.compile()
    print("--- Grafo de LangGraph compilado exitosamente con herramientas dinámicas ---")

except Exception as e:
    print(f"Error al compilar el grafo: {e}")

# from IPython.display import Image

# image_data = agent_executor.get_graph().draw_mermaid_png()
# image = Image(image_data)
# with open("graph_image.png", "wb") as f:
#      f.write(image.data)

# print(f"✅ ¡Imagen del grafo guardada con éxito")