# app/main.py

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 👈 agrega esto
from app.api2 import router as api_router

def create_app() -> FastAPI:
    load_dotenv()  
    app = FastAPI(
        title="Agente SQL en Databricks",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    return app

app = create_app()
