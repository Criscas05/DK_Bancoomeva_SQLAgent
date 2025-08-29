from dotenv import load_dotenv, find_dotenv
from msal import ConfidentialClientApplication
import os

load_dotenv(find_dotenv())

class Settings:

    class Auth:
        def __init__(self):
            client_secret: str = os.getenv("AZURE_CLIENT_SECRET")
            tenant_id: str = os.getenv("AZURE_TENANT_ID")
            authority: str = f"https://login.microsoftonline.com/{tenant_id}"
            self.client_id: str = os.getenv("AZURE_CLIENT_ID")
            #self.redirect_uri: str = os.getenv("AZURE_REDIRECT_URI")
            self.scopes_api: list[str] = [f"api://{self.client_id}/.default"]
            self.oidc_metadata_url: str = (
                f"https://login.microsoftonline.com/{tenant_id}"
                "/v2.0/.well-known/openid-configuration"
            )
            self.client_instance: ConfidentialClientApplication = ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=client_secret,
                authority=authority
            )

    class AIServices:
        def __init__(self):
            # Azure OpenAI
            self.api_key: str            = os.getenv("AZURE_OPENAI_API_KEY")
            self.endpoint: str           = os.getenv("AZURE_OPENAI_ENDPOINT")
            self.deployment_name: str    = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            self.api_version: str        = os.getenv("AZURE_OPENAI_API_VERSION")
            self.api_type: str           = os.getenv("AZURE_OPENAI_API_TYPE")

            # Embeddings
            self.embedding_model: str    = os.getenv("EMBEDDING_NAME")

            # Azure Cognitive Search
            self.search_endpoint: str    = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
            self.search_api_key: str     = os.getenv("AZURE_AI_SEARCH_API_KEY")

    class DBServices:
        def __init__(self):
            # Cosmos DB
            self.cosmos_endpoint: str    = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
            self.cosmos_key: str         = os.getenv("AZURE_COSMOS_DB_KEY")
            self.cosmos_db: str          = os.getenv("AZURE_COSMOS_DB_DATABASE")
            self.chat_container: str     = os.getenv("AZURE_COSMOS_DB_CHAT_COLLECTION")

    class DatabricksServices:
        def __init__(self):
            # Databricks
            self.host: str               = os.getenv("DATABRICKS_HOST")
            self.token: str              = os.getenv("DATABRICKS_TOKEN")
            self.http_path: str          = os.getenv("DATABRICKS_HTTP_PATH")

    def __init__(self):
        self.app_name: str            = "SoftIAService"
        self.auth      = Settings.Auth()
        self.ai         = Settings.AIServices()
        self.db         = Settings.DBServices()
        self.databricks = Settings.DatabricksServices()

# instancia única para usar en toda la app
settings = Settings()
