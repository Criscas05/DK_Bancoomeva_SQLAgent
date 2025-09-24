from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions, PartitionKey
from langchain_core.messages import message_to_dict, messages_from_dict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from decimal import Decimal
from datetime import date
from app import config
import datetime
import uuid
import json

class CosmosDBService:
    """Servicio para gestionar el historial de conversaciones en Cosmos DB."""

    def __init__(self):
        """Inicializa el cliente de Cosmos DB."""
        if not config.COSMOS_DB_ENDPOINT or not config.COSMOS_DB_KEY:
            raise ValueError("El endpoint y la clave de Cosmos DB deben estar configurados.")
        
        self.client = CosmosClient(config.COSMOS_DB_ENDPOINT, credential=config.COSMOS_DB_KEY)
        # Inicializamos los atributos a None. Se cargarán de forma asíncrona.
        self.database = None
        self.conversations_container = None
        self.results_container = None
        print("Servicio de Cosmos DB inicializado.")

    async def initialize_resources(self):
        """
        Asegura que la base de datos y ambos contenedores existen antes de que la 
        aplicación acepte peticiones.
        """
        await self._get_conversations_container()
        await self._get_results_container()
        print("Recursos de Cosmos DB listos.")

    async def _get_database(self):
        """Obtiene una referencia a la base de datos, creándola si no existe."""
        if self.database is None:
            try:
                self.database = self.client.get_database_client(config.COSMOS_DB_DATABASE_NAME)
                await self.database.read()
                print(f"Base de datos '{config.COSMOS_DB_DATABASE_NAME}' encontrada.")
            except exceptions.CosmosResourceNotFoundError:
                print(f"Creando base de datos '{config.COSMOS_DB_DATABASE_NAME}'...")
                self.database = await self.client.create_database(config.COSMOS_DB_DATABASE_NAME)
        return self.database

    async def _get_conversations_container(self):
        """Obtiene una referencia al contenedor de conversaciones, creándolo si no existe."""
        if self.conversations_container is None:
            database = await self._get_database()
            try:
                self.conversations_container = await database.create_container_if_not_exists(
                    id=config.COSMOS_DB_CONTAINER_NAME,
                    partition_key=PartitionKey(path="/sessionId"),
                )
                print(f"Contenedor '{config.COSMOS_DB_CONTAINER_NAME}' listo.")
            except Exception as e:
                print(f"Error al inicializar el contenedor de conversaciones: {e}")
        return self.conversations_container

    async def _get_results_container(self):
        """Obtiene una referencia al contenedor de resultados, creándolo si no existe."""
        if self.results_container is None:
            database = await self._get_database()
            try:
                self.results_container = await database.create_container_if_not_exists(
                    id=config.COSMOS_DB_RESULTS_CONTAINER_NAME,
                    partition_key=PartitionKey(path="/sessionId"),
                )
                print(f"Contenedor '{config.COSMOS_DB_RESULTS_CONTAINER_NAME}' listo.")
            except Exception as e:
                print(f"Error al inicializar el contenedor de resultados: {e}")
        return self.results_container

    #--- NUEVO MÉTODO AUXILIAR: De Objeto a Diccionario Optimizado
    def _message_to_slim_dict(self, message) -> dict:
        """Convierte un objeto de mensaje de LangChain a un diccionario optimizado para el almacenamiento."""
        msg_dict = {"type": message.type, "content": message.content}
        if isinstance(message, AIMessage) and message.tool_calls:
            # Para AIMessage, solo nos importan las llamadas a herramientas.
            msg_dict["tool_calls"] = message.tool_calls
        elif isinstance(message, ToolMessage):
            # Para ToolMessage, necesitamos el ID de la llamada y el nombre de la herramienta.
            msg_dict["tool_call_id"] = message.tool_call_id
            msg_dict["name"] = message.name
        return msg_dict

    # --- NUEVO MÉTODO AUXILIAR: De Diccionario Optimizado a Objeto ---
    def _slim_dict_to_message(self, msg_dict: dict):
        """Reconstruye un objeto de mensaje de LangChain desde un diccionario optimizado."""
        msg_type = msg_dict.pop("type")
        if msg_type == "human":
            return HumanMessage(**msg_dict)
        elif msg_type == "ai":
            return AIMessage(**msg_dict)
        elif msg_type == "tool":
            return ToolMessage(**msg_dict)
        else:
            raise ValueError(f"Tipo de mensaje desconocido: {msg_type}")

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> list:
        """
        Recupera los últimos 'limit' mensajes de una conversación, reconstruyendo
        los objetos de mensaje desde el formato optimizado.
        """
        container = await self._get_conversations_container()
        # Hacemos la consulta más eficiente ordenando y limitando en la propia base de datos.
        query = f"SELECT * FROM c WHERE c.sessionId = @session_id ORDER BY c.timestamp DESC OFFSET 0 LIMIT {limit}"
        parameters = [{"name": "@session_id", "value": session_id}]
        
        try:
            items_iterable = container.query_items(query=query, parameters=parameters, partition_key=session_id)
            # El resultado de la BD viene en orden descendente, lo revertimos para la lógica del agente.
            items = [item async for item in items_iterable][::-1] 
            
            # Reconstruimos los objetos de mensaje de LangChain desde los diccionarios guardados.
            history = [self._slim_dict_to_message(msg['message_data']) for msg in items]
            
            print(f"Historial recuperado para la sesión {session_id}: {len(history)} mensajes.")
            return history
        except exceptions.CosmosHttpResponseError as e:
            print(f"Error al consultar el historial para la sesión {session_id}: {e}")
            return []

    async def add_messages(self, session_id: str, messages: list):
        """
        Añade una lista de mensajes de LangChain (Human, AI, Tool) al historial,
        guardando la estructura completa de cada mensaje.
        """
        container = await self._get_conversations_container()
        
        for message in messages:
            # Serializamos el objeto de mensaje completo a un diccionario.
            # message_dict = message_to_dict(message)
            # --- Usamos nuestro nuevo helper para serializar ---
            message_slim_dict = self._message_to_slim_dict(message)

            new_item = {
                "id": f"{session_id}-{datetime.datetime.utcnow().timestamp()}-{message.type}",
                "sessionId": session_id,
                "message_data": message_slim_dict, # Guardamos el objeto completo.
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            }
            try:
                await container.create_item(body=new_item)
            except exceptions.CosmosHttpResponseError as e:
                print(f"Error al añadir mensaje a la sesión {session_id}: {e}")
        
        print(f"Se añadieron {len(messages)} mensajes a la sesión {session_id}.")

    async def save_query_result(self, session_id: str, message_id: str, result_data: dict):
        """
        Guarda el resultado completo de una consulta en el Storage.
        Guarda una muestra del resultado completo de una consulta en CosmosDB.
        """
        container = await self._get_results_container()
        RESULTS_LIMIT_FOR_THE_FRONTEND = int(config.RESULTS_LIMIT_FOR_THE_FRONTEND)

        sample_rows = result_data["rows"][:RESULTS_LIMIT_FOR_THE_FRONTEND]
        # --- Lógica de Conversión de Tipos de Datos ---
        processed_rows = []
        for row in sample_rows:
            processed_row = {}
            for k, v in dict(zip(result_data["columns"], row)).items():
                if isinstance(v, date):
                    processed_row[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    # Convertimos el objeto Decimal a un float, que es serializable.
                    processed_row[k] = float(v)
                else:
                    processed_row[k] = v
            processed_rows.append(processed_row)

        # Estructura final
        data_sample = {
            "columns": result_data["columns"],
            "rows": processed_rows
        }

        item = {
            "id": str(uuid.uuid4()),
            "sessionId": session_id,
            "messageId": message_id,
            "data": data_sample,
            "type": "query_result"
        }

        await container.upsert_item(item)
        print(f"Resultado para message_id '{message_id}' guardado en Cosmos DB.")

    async def get_query_result(self, session_id: str, message_id: str) -> dict | None:
        """Recupera un resultado de consulta guardado desde Cosmos DB."""
        container = await self._get_results_container()
        try:

            query = "SELECT * FROM c WHERE c.messageId = @msg_id"
            items = container.query_items(
                query=query,
                parameters=[{"name": "@msg_id", "value": message_id}],
                partition_key=session_id
            )

            async for item in items:
                
                return item
                
        except exceptions.CosmosResourceNotFoundError:
            print(f"No se encontró el resultado para message_id '{message_id}' en la sesión '{session_id}'.")
            return None
        except Exception as e:
            print(f"Error inesperado al recuperar el resultado: {e}")
            return None
