import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde un archivo .env
# Es útil para el desarrollo local. En producción, las variables se
# inyectan directamente en el entorno que sería Azure Container Apps.
load_dotenv()

# --- Configuración de OpenAI ---
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4o-sql-agent")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_EMBEDDING_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_NAME")

# --- Configuración de Azure Cosmos DB ---
COSMOS_DB_ENDPOINT = os.getenv("COSMOS_DB_ENDPOINT")
COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY")
COSMOS_DB_DATABASE_NAME = os.getenv("COSMOS_DB_DATABASE_NAME", "db_agentesql")
COSMOS_DB_CONTAINER_NAME = os.getenv("COSMOS_DB_CONTAINER_NAME", "historialconversaciones")
COSMOS_DB_RESULTS_CONTAINER_NAME = os.getenv("COSMOS_DB_RESULTS_CONTAINER_NAME", "resultadosquerysql")

# --- Configuración de Azure Storage ---
AZURE_STORAGE_SAS_TOKEN = os.getenv("AZURE_STORAGE_SAS_TOKEN")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "data-processed")
AZURE_STORAGE_ACCOUNT_URL = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
AZURE_STORAGE_BLOB_PREFIX = os.getenv("AZURE_STORAGE_BLOB_PREFIX", "")

# --- Configuración de Databricks ---
DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

# --- Información del esquema de Databricks para el Agente ---
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG")
DATABRICKS_SCHEMA = os.getenv("DATABRICKS_SCHEMA")
DATABRICKS_TABLE = os.getenv("DATABRICKS_TABLE")

# --- Configuración de Azure AI Search ---
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "index_sqlagent")

# --- Agent Configuration ---
CONVERSATION_HISTORY_WINDOW = os.getenv("CONVERSATION_HISTORY_WINDOW")
RESULTS_LIMIT_FOR_THE_AGENT = os.getenv("RESULTS_LIMIT_FOR_THE_AGENT")
RESULTS_LIMIT_FOR_THE_FRONTEND = os.getenv("RESULTS_LIMIT_FOR_THE_FRONTEND")

# Validar que las variables críticas están presentes
if not all([AZURE_OPENAI_API_KEY, COSMOS_DB_ENDPOINT, COSMOS_DB_KEY, DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN]):
    raise ValueError("Faltan una o más variables de entorno críticas. Revisa el archivo .env o la configuración del entorno.")
