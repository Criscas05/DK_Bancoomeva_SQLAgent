# app/api.py
from fastapi import Query, Depends
from typing import Optional
from fastapi.responses import JSONResponse
from app.db_connection import run_databricks_query
import re
import ast
import traceback
from langchain_core.messages import ToolMessage, AIMessage
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.sql_agent import get_sql_graph_agent
from app.tools import db_query_tool
from app.azure_search import AzureSearchService
from app.services.cosmos_db import cosmos_manager
from app.core.auth import get_current_user

router = APIRouter()

class QueryModel(BaseModel):
    question: str
    catalog: str
    schema: str
    instructions: Optional[str] = None
    corrected_sql_query: Optional[str] = None

class TestQueryModel(BaseModel):
    question: str

class StoreSQLModel(BaseModel):
    question: str
    sql_query: str
    catalog: str
    db_schema: str

class RecoverChatmodel(BaseModel):
    jwt:str
    user_id:str



def parse_query_result(raw_text: str) -> dict:
    """
    Convierte el texto devuelto por Databricks ('Columns: [...]' y 'Row(...)')
    en un diccionario {"columns": [...], "rows": [...]} con fechas formateadas.
    """
    result = {"columns": [], "rows": []}

    col_re  = re.compile(r"^Columns:\s*\[(.*)\]")
    row_re  = re.compile(r"^Row\((.*)\)")
    kv_re   = re.compile(r'(\w+)=((?:datetime\.(?:date|datetime)\([^\)]*\))|[^,]+)(?:, |$)')

    for line in raw_text.splitlines():
        line = line.strip()

        m_cols = col_re.match(line)
        if m_cols:
            try:
                cols = ast.literal_eval("[" + m_cols.group(1) + "]")
                if isinstance(cols, list):
                    result["columns"] = cols
            except Exception:
                pass
            continue

        m_row = row_re.match(line)
        if not m_row:
            continue

        row_inner = m_row.group(1)
        row_dict  = {}

        for kv in kv_re.finditer(row_inner):
            k = kv.group(1)
            v = kv.group(2).strip()

            if v.startswith(("datetime.datetime(", "datetime.date(")):
                inside = v[v.index("(") + 1 : v.rindex(")")]
                parts  = [p.strip() for p in inside.split(",")]
                if len(parts) >= 3:
                    y, m, d = parts[:3]
                    if v.startswith("datetime.datetime("):
                        h = parts[3] if len(parts) > 3 else "0"
                        n = parts[4] if len(parts) > 4 else "0"
                        row_dict[k] = f"{y.zfill(4)}-{m.zfill(2)}-{d.zfill(2)}T{h.zfill(2)}:{n.zfill(2)}:00"
                    else:
                        row_dict[k] = f"{y.zfill(4)}-{m.zfill(2)}-{d.zfill(2)}"
                else:
                    row_dict[k] = v

            elif v.startswith("Decimal(") and "(" in v and ")" in v:
                from decimal import Decimal, InvalidOperation
                raw_num = v[v.index("(") + 1 : v.rindex(")")]
                num_str = raw_num.strip("'\"")
                try:
                    d = Decimal(num_str)
                except InvalidOperation:
                    cleaned = re.sub(r"[^0-9eE\+\-\.]", "", num_str)
                    try:
                        d = Decimal(cleaned)
                    except InvalidOperation:
                        d = Decimal("0")
                row_dict[k] = float(d)
                continue

            else:
                raw_val = v.strip("'")
                try:
                    row_dict[k] = float(raw_val)
                except ValueError:
                    row_dict[k] = raw_val

        result["rows"].append(row_dict)

    return result




def format_probable_fields(result_dict: dict) -> dict:
    """
    Dado un resultado con formato {"columns": [...], "rows": [{...}, ...]},
    retorna una copia del resultado donde:
    - los campos de dinero se formatean como strings tipo "$1,234.56"
    - los campos de porcentaje se formatean como "12.34%"
    """
    money_keywords = ['importe', 'monto', 'valor', 'total', 'costo', 'precio', 'totalImportePedido']
    never_money_keywords = ['id', 'codigo', 'número', 'num', 'cliente_id', 'horas']
    percent_keywords = ['porcentaje', 'pct', 'percent']  # claves para detectar porcentajes

    formatted_result = {
        "columns": result_dict.get("columns", []),
        "rows": []
    }

    for row in result_dict.get("rows", []):
        formatted_row = {}
        for key, val in row.items():
            original_key = key.lower()

            # formatear campos de porcentaje
            if isinstance(val, (int, float)) and any(kw in original_key for kw in percent_keywords):
                pct = val * 100 if abs(val) <= 1 else val
                formatted_row[key] = f"{pct:.2f}%"
                continue

            if isinstance(val, (int, float)) and 'promedio' in original_key:
                formatted_row[key] = f"{val:.2f}"
                continue

            if isinstance(val, (int, float)) and 'totalhoras' in original_key:
                formatted_row[key] = f"{val:.2f}"
                continue

            # Lógica para dinero
            is_money_candidate = (
                isinstance(val, (int, float))
                and any(kw in original_key for kw in money_keywords)
                and not any(kw in original_key for kw in never_money_keywords)
                and abs(val) >= 100
            )

            if is_money_candidate:
                try:
                    formatted_row[key] = f"${val:,.2f}"
                except Exception:
                    formatted_row[key] = val
            else:
                formatted_row[key] = val

        formatted_result["rows"].append(formatted_row)

    return formatted_result


@router.post("/ask")
async def ask_sql(query: QueryModel, user_data: dict = Depends(get_current_user)):
    try:
        user_messages = [("user", query.question)]

        if query.corrected_sql_query:
            user_messages.append(
                (
                    "user",
                    f"""El usuario ha provisto manualmente la siguiente consulta SQL
                    y desea ejecutarla en lugar de la generada automáticamente:
                    {query.corrected_sql_query}
                    """
                )
            )

        graph = get_sql_graph_agent()
        result = await graph.ainvoke({
            "messages": user_messages,
            "catalog": query.catalog,
            "schema": query.schema,
            "extra_instructions": query.instructions or "Ten en cuenta muy bien todas estas instrucciones.",
        })
        messages = result["messages"]

        final_answer = None
        last_query = None
        last_query_result = None
        last_db_tool_call_id = None

        for msg in messages:
            tool_calls = getattr(msg, "tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    if tc["name"] == "db_query_tool":
                        last_query = tc["args"].get("query")
                        last_db_tool_call_id = tc["id"]
                    if tc["name"] == "SubmitFinalAnswer_tool":
                        final_answer = tc["args"].get("final_answer")

            if isinstance(msg, ToolMessage):
                if last_db_tool_call_id and msg.tool_call_id == last_db_tool_call_id:
                    last_query_result = msg.content

        if not final_answer:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage) and last_msg.content.strip():
                final_answer = last_msg.content
            else:
                final_answer = "No se generó una respuesta final."

        parsed_dict = {}
        if isinstance(last_query_result, str) and "Query:" in last_query_result:
            parsed_dict = parse_query_result(last_query_result)
            parsed_dict = format_probable_fields(parsed_dict)
        else:
            if isinstance(last_query_result, str):
                parsed_dict = {"raw": last_query_result}
            elif last_query_result:
                parsed_dict = {"raw": str(last_query_result)}

        print("SQL RESULT", parsed_dict)

        cosmos_manager.save_or_update_thread(
            user_id= user_data.get("user_id"), # "example_auth0|648fd12a7c34aa00125a4b98",  # Definir con los datos futuros que vendrán del frontend
            user_email="leche.liquida@alqueria.co",
            user_message=query.question,
            user_instructions=query.instructions,
            corrected_sql_query=query.corrected_sql_query,
            sql_query=last_query,
            sql_result=parsed_dict,
            final_answer=final_answer
        )

        return {
            "answer": final_answer or "",
            "sql_query": last_query or "",
            "sql_result": parsed_dict  
        }

    except Exception as e:
        print("=== EXCEPCION DETECTADA ===")
        traceback.print_exc()  
        raise HTTPException(status_code=400, detail=f"Error interno: {str(e)}")


@router.post("/test-db-query")
def test_db_query(req: TestQueryModel):
    try:
        # Prueba directa de db_query_tool
        result = db_query_tool(req.question)
        return {"result": result}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recover-chat")
async def recover_chat(payload: RecoverChatmodel, user_data: dict = Depends(get_current_user)):
    """
    Endpoint de prueba que recupera la conversación completa
    de un user_id específico en Cosmos DB.
    """
    try:
        # 🔥 Hardcode user_id para pruebas
        # user_id = "example_auth0|648fd12a7c34aa00125a4b98"
        user_id = user_data.get("user_id")

        result=cosmos_manager.get_chat_history_by_user_id(user_id)

        if result is None:
            return {"message": f"No se encontró conversación para el user_id {user_id}"}
        
        return result

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en recover-chat-test: {str(e)}")


@router.get("/catalogs")
def list_catalogs():
    """
    Lista los catálogos disponibles en Databricks,
    usando db_query_tool + parse_query_result.
    """
    try:
        raw = db_query_tool("SHOW CATALOGS")
        parsed = parse_query_result(raw)
        catalogs = []
        for r in parsed["rows"]:
            cat = r.get("catalog")
            if isinstance(cat, str):
                catalogs.append(cat)

        return {"catalogs": catalogs}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/schemas")
def list_schemas(catalog: str = Query(..., description="Catálogo seleccionado")):
    """
    Lista los schemas para un catálogo, usando db_query_tool + parse_query_result.
    """
    try:
        raw = db_query_tool(f"SHOW SCHEMAS IN {catalog}")
        parsed = parse_query_result(raw)
        schemas = []
        col_names = parsed.get("columns", [])
        key_for_schema = None
        for possible_col in ["databaseName", "namespace", "schemaName"]:
            if possible_col in col_names:
                key_for_schema = possible_col
                break
        if not key_for_schema:
            key_for_schema = "databaseName"  

        for r in parsed["rows"]:
            sch = r.get(key_for_schema)
            if isinstance(sch, str):
                schemas.append(sch)

        return {"schemas": schemas}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/save-sql")
async def save_sql(payload: StoreSQLModel):
    """
    Endpoint para guardar la pregunta y la SQL aprobada por el usuario
    en Azure Cognitive Search.
    """
    try:
        azure_svc = AzureSearchService(index_name="agent-sql-index-v2")
        # 1) Crea/actualiza el índice (por si no existe)
        await azure_svc.create_or_update_index()

        # 2) Sube/actualiza el doc (upsert) usando question como key
        await azure_svc.upsert_document(
            question=payload.question,
            sql_query=payload.sql_query,
            catalog=payload.catalog,
            db_schema=payload.db_schema
        )

        return {"message": "SQL guardada correctamente en Azure Search"}

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}