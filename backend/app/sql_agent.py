# app/sql_agent.py

import os
import re, math
from typing_extensions import TypedDict
from typing import Annotated
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.messages import AIMessage, ToolMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# Fallback
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langgraph.prebuilt import ToolNode

from app.azure_openai import get_azure_openai_llm
from app.tools import sql_db_list_tables, sql_db_schema, db_query_tool, search_stored_query_tool

###############################################################################
# 1) Estado + Tools
###############################################################################
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    catalog: str
    schema: str
    extra_instructions: str

class SubmitFinalAnswer(BaseModel):
    """Respuesta final p/usuario."""
    final_answer: str = Field(..., description="Respuesta final al usuario")

@tool(description="Devuelve la respuesta final al usuario.")
def SubmitFinalAnswer_tool(final_answer: str) -> str:
    """
    Herramienta para cerrar la conversación con la respuesta final.
    """
    return final_answer

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error al ejecutar la herramienta:\n{repr(error)}",
                tool_call_id=tc["id"]
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list):
    node = ToolNode(tools)
    return node.with_fallbacks([RunnableLambda(handle_tool_error)], exception_key="error")

###############################################################################
# 2) Prompt del sistema
###############################################################################
SYSTEM_INSTRUCTIONS = """\
Eres un asistente experto en SQL Databricks (estilo ReAct).
1) Si no estás seguro de las columnas de la tabla, primero llama a sql_db_schema.
2) Usa la información del schema para encontrar la columna real (por ejemplo, en vez de 'importe total' podría ser 'TOTAL_PED_IMPORTE').
3) Si una tabla contiene una clave como 'codigo_producto', busca si existe otra tabla que contenga detalles de ese producto (como nombre o descripción), y haz un JOIN para obtener esa información.
4) Usa la información del schema para saber cómo hacer el JOIN, basándote en claves como 'CodProducto', 'id_cliente', etc.
5) Luego, con la columna correcta, llama a db_query_tool con la consulta final.
6) Para buscar o seleccionar información de las tablas usa siempre el formato <catalogo>.<schema>.<tabla>. ejemplo: consumption_dev.gtm.fac_pedidos_ventas.
7) Cuando termines, llama a SubmitFinalAnswer_tool(final_answer="...") con texto no vacío.
8) Si detectas un error con los nombres de columnas, reintenta consultando el schema antes de volver a db_query_tool.
9) Evita loops infinitos. Una vez tengas la columna real, genera la consulta final.
10) No uses funciones de fechas que devuelvan objetos datetime como DATE_TRUNC, DATE_PART o similares. Usa funciones que devuelvan strings como DATE_FORMAT o DATE_ADD.
11) Si no puedes responder la pregunta, llama a SubmitFinalAnswer_tool(final_answer="No hay datos para responder esta pregunta.") y termina la conversación.
12) Si no puedes encontrar la tabla, llama a sql_db_list_tables y luego a sql_db_schema para ver el esquema de la tabla.
13) Si necesitas formatear fechas, puedes usar DATE_FORMAT(columna, '%Y-%m') para que el resultado sea un string como '2024-10'.
14) Si detectas que el usuario proporciona manualmente una consulta SQL en su mensaje, ejecútala directamente usando db_query_tool y luego llama a SubmitFinalAnswer_tool(final_answer="...") con una respuesta conversacional.
15) Si encontraste en el índice una query previa aprobada (por medio de search_stored_query_tool), Compara la pregunta original recuperada desde el índice (original_question) con la nueva actual (user_question). Si son esencialmente la misma consulta, reutiliza la SQL del índice tal cual. Si difieren (por ejemplo, otra fecha, otro producto), ajusta la query manteniendo la misma estructura.
"""

USER_PLACEHOLDER = "{messages}"

def build_final_instructions(base_instructions: str, extra: str) -> str:
    """
    Retorna la concatenación de las instrucciones base y las extras del usuario.
    Si extra está vacío, solo retorna base.
    """
    if extra and extra.strip():
        return base_instructions.strip() + "\n\n16) " + extra.strip()
    else:
        return base_instructions

all_tools = [
    sql_db_list_tables,
    sql_db_schema,
    db_query_tool,
    SubmitFinalAnswer_tool,
    search_stored_query_tool
]

###############################################################################
# 3) Nodo ReAct con fallback final
###############################################################################
async def react_node(state: State):
    """
    Único nodo que maneja múltiples pasos en una sola invocación:
     - Llama al LLM
     - Si hay una tool_call, la ejecuta
     - Agrega el resultado y repite
     - Si no llama a SubmitFinalAnswer_tool, forzamos un fallback
    """
    MAX_STEPS = 10
    last_query = None

    extra_instr = state.get("extra_instructions", "")

    final_system_instructions = build_final_instructions(SYSTEM_INSTRUCTIONS, extra_instr)

    local_chat_prompt = ChatPromptTemplate.from_messages([
        ("system", final_system_instructions),
        ("placeholder", USER_PLACEHOLDER)
    ])

    local_llm_chain = (local_chat_prompt | get_azure_openai_llm().bind_tools(all_tools))


    # --------------------------------------------------------------------------
    # Revisar si hay una query almacenada en el índice
    # --------------------------------------------------------------------------
    # Tomamos el último mensaje de usuario:
    user_question = ""
    for m in reversed(state["messages"]):
        # 1) Mensajes LangChain
        if isinstance(m, BaseMessage) and getattr(m, "type", "") == "human":
            user_question = m.content.strip()
            break
        # 2) Tuplas ("user", texto)
        if isinstance(m, (tuple, list)) and len(m) == 2 and m[0] == "user":
            user_question = m[1].strip()
            break
        # 3) Diccionarios {"role": "user", ...}
        if isinstance(m, dict) and m.get("role") == "user":
            user_question = m.get("content", "").strip()
            break
    print("🟡 user_question extraído:", user_question)

    # Forzamos la llamada a search_stored_query_tool
    forced_call_msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "search_stored_query_tool",
            "args": {
                "query": user_question,
                "catalog": state["catalog"],
                "db_schema": state["schema"]
            },
            "id": "forced_search_stored_query"
        }]
    )
    state["messages"].append(forced_call_msg)

    print("FORCED tool call to search_stored_query_tool with:", user_question)

    # Ejecutamos la tool (aquí run_sync; si usas async, ajusta)
    search_result = await search_stored_query_tool.arun({
        "query": user_question,
        "catalog": state["catalog"],
        "db_schema": state["schema"]
    })

    print("search_stored_query_tool returned:", search_result)
    
    state["messages"].append(
        ToolMessage(
            content=search_result,
            tool_call_id="forced_search_stored_query"
        )
    )

    # 2) Si el tool dice MATCH_FOUND, NO ejecutamos ciegamente la query.
    #    En su lugar, la añadimos como un "mensaje de sistema" o "assistant"
    #    para que el LLM la use como referencia (paso 15 de las instrucciones).
    if search_result.startswith("MATCH_FOUND:"):
        try:
            # Regex para extraer original_question, sql_query y score
            pattern = r"MATCH_FOUND:\s*original_question=(.*?),\s*sql_query=(.*?),\s*score=([\d\.]+)"
            match = re.search(pattern, search_result)
            if match:
                original_question = match.group(1).strip()
                candidate_sql = match.group(2).strip()
                match_score = match.group(3).strip()

                # Inyectar la query recuperada + original_question
                ref_message = AIMessage(
                    role="system",
                    content=(
                        "He recuperado esta SQL aprobada del índice.\n"
                        f"- Pregunta original: '{original_question}'\n"
                        f"- SQL aprobada:\n{candidate_sql}\n"
                        f"- Score de similitud: {match_score}\n\n"
                        "La nueva pregunta del usuario es:\n"
                        f"'{user_question}'\n\n"
                        "Si son esencialmente la misma intención, reutiliza la SQL tal cual.\n"
                        "Si difiere (por ejemplo, otra fecha, etc.), ajusta la query "
                        "manteniendo la misma estructura. "
                    )
                )
                state["messages"].append(ref_message)

        except Exception as ex:
            print("Error parseando MATCH_FOUND:", ex)

    # --------------------------------------------------------------------------
    # FIN de la lógica para reusar la query si fue hallada.
    # --------------------------------------------------------------------------

    total_prompt_tokens     = 0   
    total_completion_tokens = 0

    for step_i in range(MAX_STEPS):

        try:
            llm_response = await local_llm_chain.ainvoke({"messages": state["messages"]})

            token_usage = getattr(llm_response, "response_metadata", {}).get("token_usage", {})

            if token_usage:
                print(f"✅ Token usage: Prompt={token_usage.get('prompt_tokens', '?')}, "
                      f"Completion={token_usage.get('completion_tokens', '?')}, "
                      f"Total={token_usage.get('total_tokens', '?')}")
                #state["token_usage"] = token_usage  # opcional para guardar

                total_prompt_tokens     += token_usage.get("prompt_tokens", 0)
                total_completion_tokens += token_usage.get("completion_tokens", 0)
                
            else:
                print("❌ Token usage no disponible.")

        except Exception as e:

            error_message = str(e)
            print(f"❌ Error al invocar Azure OpenAI:", error_message)

            # Manejo de Rate Limit
            if "429" in error_message:
                wait_time = 60
                match = re.search(r"retry after (\d+) seconds", error_message.lower())
                if match:
                    wait_time = int(match.group(1))

                if wait_time > 3599:
                    msg = f"Superaste el límite de tokens de OpenAI. Intenta en {math.ceil(wait_time / 3600)} horas."
                elif wait_time > 59:
                    msg = f"Superaste el límite de tokens de OpenAI. Intenta en {math.ceil(wait_time / 60)} minutos."
                else:
                    msg = f"Superaste el límite de tokens de OpenAI. Intenta en {wait_time} segundos."
            else:
                msg = "Se produjo un error inesperado al llamar al modelo. Intenta de nuevo más tarde."

            forced_final = AIMessage(
                content="",                
                tool_calls=[{
                    "name": "SubmitFinalAnswer_tool",
                    "args": {"final_answer": msg},
                    "id": "forced_submit"
                }]
            )

            return {"messages": [forced_final]}

        print(f"\n=== Step {step_i} - LLM Response ===")
        print("Content:", llm_response.content)
        print("Tool calls:", llm_response.tool_calls)

        if llm_response.tool_calls:
            # Agregamos el mensaje del LLM a la conversación
            state["messages"].append(llm_response)

            # Recorremos cada tool_call devuelta en esta iteración
            for tc in llm_response.tool_calls:
                tool_name = tc["name"]
                if tool_name == "SubmitFinalAnswer_tool":
                    # Fin: regresamos ese mensaje
                    return {"messages": [llm_response]}

                elif tool_name in ["sql_db_list_tables", "sql_db_schema", "db_query_tool"]:
                    tool_args = tc["args"]

                    if tool_name == "sql_db_list_tables":
                        tool_args["catalog"] = state["catalog"]
                        tool_args["schema"] = state["schema"]
                        result = sql_db_list_tables(**tool_args)

                    elif tool_name == "sql_db_schema":
                        tool_args["catalog"] = state["catalog"]
                        tool_args["schema"] = state["schema"]
                        result = sql_db_schema(**tool_args)

                    else:  # db_query_tool
                        query_str = tool_args["query"]
                        # Evitar bucle de la misma query
                        if query_str == last_query:
                            # Armamos un SubmitFinalAnswer con la última respuesta
                            last_tool_msg = next(
                                (m for m in reversed(state["messages"]) if isinstance(m, ToolMessage)), 
                                None
                            )
                            fallback_ans = last_tool_msg.content if last_tool_msg else "No se generó respuesta final."
                            forced_final = AIMessage(
                                content="",
                                tool_calls=[{
                                    "name": "SubmitFinalAnswer_tool",
                                    "args": {"final_answer": fallback_ans},
                                    "id": "forced_submit"
                                }]
                            )
                            return {"messages": [forced_final]}
                        last_query = query_str
                        result = db_query_tool(query_str)

                    state["messages"].append(
                        ToolMessage(content=result, tool_call_id=tc["id"])
                    )

            # Tras manejar TODAS las tool_calls, pasamos a la siguiente iteración
            continue

        else:
            # No hay tool_calls en este paso
            if llm_response.content.strip():
                return {"messages": [llm_response]}

            # Sino, fallback => tomamos la última ToolMessage
            last_tool_msg = next(
                (m for m in reversed(state["messages"]) if isinstance(m, ToolMessage)), 
                None
            )
            fallback_ans = last_tool_msg.content if last_tool_msg else "No se generó respuesta final."

            forced_final = AIMessage(
                content="",
                tool_calls=[{
                    "name": "SubmitFinalAnswer_tool",
                    "args": {"final_answer": fallback_ans},
                    "id": "forced_submit"
                }]
            )
            return {"messages": [forced_final]}

    # Si no cierra en MAX_STEPS => forzamos final
    forced_final = AIMessage(
        content="",
        tool_calls=[{
            "name": "SubmitFinalAnswer_tool",
            "args": {"final_answer": "Se alcanzó el máximo de pasos."},
            "id": "forced_submit"
        }]
    )
    return {"messages": [forced_final]}

###############################################################################
# 4) Construir el Grafo con un solo nodo
###############################################################################
def build_graph_agent():
    workflow = StateGraph(State)
    workflow.add_node("react_node", react_node)
    workflow.add_edge(START, "react_node")
    workflow.add_edge("react_node", END)
    return workflow.compile()

def get_sql_graph_agent():
    return build_graph_agent()
