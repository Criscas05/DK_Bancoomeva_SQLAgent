##cosmos_db.py
import os

from dotenv import load_dotenv

from typing import Dict, Optional
from datetime import datetime
from azure.cosmos import CosmosClient as AzureCosmosClient, PartitionKey, exceptions
from app.core.utils import TimeManager

import uuid

load_dotenv() 

settings_dict = {
    "cosmos":{
        "endpoint": os.getenv("AZURE_COSMOS_DB_ENDPOINT"),
        "key": os.getenv("AZURE_COSMOS_DB_KEY"),
        "database": os.getenv("AZURE_COSMOS_DB_DATABASE"),
        "collection_chat": os.getenv("AZURE_COSMOS_DB_CHAT_COLLECTION")
        # "": os.getenv("")
    }
}

# Codigo provicional para convertir settings_dict de dict a objeto con parametros 
from types import SimpleNamespace
settings= SimpleNamespace(**{
    "cosmos": SimpleNamespace(**settings_dict["cosmos"])
})

class CosmosClient:
    """
    Cliente para interactuar con Cosmos DB usando la API for NoSQL (SDK nativo).
    """
    def __init__(self) -> None:
        self.client = AzureCosmosClient(settings.cosmos.endpoint, settings.cosmos.key)
        self.db = self.client.get_database_client(settings.cosmos.database)
        self.chat_container = self.db.get_container_client(settings.cosmos.collection_chat)

    def get_chat_container(self):
        return self.chat_container


class CosmosService:
    def __init__(self, client: CosmosClient):
        self.client = client
        self.chat_container = self.client.get_chat_container()

    def save_or_update_thread(self, user_id: str, user_email: str, user_message: str, user_instructions: str, corrected_sql_query: Optional[str], sql_query: Optional[str], sql_result: Dict, final_answer: str) -> None:
        try:
            query = "SELECT * FROM c WHERE c.user_id = @user_id"
            params = [{"name": "@user_id", "value": user_id}]
            items = list(self.chat_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))

            # now = datetime.utcnow().isoformat() + "Z"
            now = TimeManager.current_time(to_str=True)

            # Construir el mensaje del usuario
            user_entry = {
                "id": str(uuid.uuid4()), # Acutalizar con el criterio
                "role": "user",
                "timestamp": now,
                "content": user_message,
                "instructions": user_instructions,
                "corrected_sql_query": corrected_sql_query
            }

            # Construir el mensaje del agente
            agent_entry = {
                "id": str(uuid.uuid4()), # Acualizar con el criterio
                "role": "agent",
                "timestamp": now,
                "sql_query": sql_query,
                "sql_result": sql_result,
                "final_answer": final_answer
            }

            if items:
                doc = items[0]
                doc["messages"].append(user_entry)
                doc["messages"].append(agent_entry)
                doc["last_interaction_time"]= now
                self.chat_container.replace_item(item=doc["id"], body=doc)
            else:
                session_id = f"{user_id}#{uuid.uuid4()}"# TimeManager.generate_session_id(user_email) # f"{user_id}#{TimeManager.generate_timestamp_uuid_id()}" 

                new_document = {
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,  # ID único obligatorio
                    "user_id": user_id,
                    "init_time": TimeManager.current_time(to_str=True),
                    "last_interaction_time": now,
                    "messages": [user_entry, agent_entry]
                }
                self.chat_container.create_item(body=new_document)

        except Exception as e:
            print(f"Error al guardar el hilo: {e}")


    def get_chat_history_by_user_id(self, user_id: str) -> Optional[dict]:
        """
        Recupera el historial de chat para un user_id específico.
        Devuelve el documento tal como está en Cosmos DB.
        """
        try:
            query = "SELECT * FROM c WHERE c.user_id = @user_id"
            params = [{"name": "@user_id", "value": user_id}]
            
            items = list(self.chat_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            ))
            
            if not items:
                return None

            # Devuelve el documento completo tal cual está en Cosmos DB
            doc = items[0]
            # Claves que quieres mantener
            allowed_keys = {"id", "session_id", "user_id", "messages"}

            # Crear un nuevo dict solo con las claves permitidas
            filtered_doc = {k: v for k, v in doc.items() if k in allowed_keys}

            return filtered_doc
        
        except Exception as e:
            print(f"Error al recuperar historial de chat: {e}")
            return None



# Instancia global para importar en otros modulos
cosmos_manager = CosmosService(client=CosmosClient())
