from pathlib import Path
import logging
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse

from app import config
from app.rtmt import RTMiddleTier
from app.prompts import system_prompt
from app.tools import search_products_text_tool


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-fastapi")

# ── Singleton del middle-tier que hace el puente con OpenAI ───────────────────
rtmt = RTMiddleTier(
    endpoint=config.AZURE_OPENAI_ENDPOINT,
    deployment=config.OPENAI_DEPLOYMENT_REALTIME,
    api_key=config.AZURE_OPENAI_API_KEY,
    api_version=config.OPENAI_API_VERSION_REALTIME,
    system_prompt=system_prompt,
)

rtmt.add_tool(search_products_text_tool)

# ── FastAPI ────────────────────────────────────────────────────────────────────
app = FastAPI(title="Realtime-Voice-Demo")

frontend_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"

@app.get("/{full_path:path}")
async def serve_static(full_path: str):
    file_path = frontend_dir / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    # fallback: index.html (para SPA / React Router)
    return FileResponse(frontend_dir / "index.html")

# Servir index.html en la raíz
@app.get("/")
async def serve_react():
    return HTMLResponse((frontend_dir / "index.html").read_text(encoding="utf-8"))

# ▶ WebSocket principal
@app.websocket("/realtime")
async def realtime_ws(ws: WebSocket):
    await ws.accept()
    try:
        await rtmt.forward_messages(ws)
    except WebSocketDisconnect:
        logger.info("Cliente desconectado (WebSocketDisconnect)")
    except Exception as e:
        logger.error("Error inesperado en realtime_ws: %s", e)
