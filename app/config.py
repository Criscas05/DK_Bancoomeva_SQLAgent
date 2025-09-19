import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# ===============================
# 🔑 Azure OpenAI - Embeddings
# ===============================
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

# ===============================
# 🔑 Azure OpenAI - Realtime
# ===============================
OPENAI_DEPLOYMENT_REALTIME = os.getenv("OPENAI_DEPLOYMENT_REALTIME")
OPENAI_API_VERSION_REALTIME = os.getenv("OPENAI_API_VERSION_REALTIME")

# ===============================
# 🔎 Azure Cognitive Search
# ===============================
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

# ===============================
# 🔒 Validación
# ===============================
_required = {
    "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
    "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
    "AZURE_OPENAI_API_VERSION": AZURE_OPENAI_API_VERSION,
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
    "OPENAI_DEPLOYMENT_REALTIME": OPENAI_DEPLOYMENT_REALTIME,
    "OPENAI_API_VERSION_REALTIME": OPENAI_API_VERSION_REALTIME,
    "AZURE_SEARCH_ENDPOINT": AZURE_SEARCH_ENDPOINT,
    "AZURE_SEARCH_KEY": AZURE_SEARCH_KEY,
    "AZURE_SEARCH_INDEX": AZURE_SEARCH_INDEX,
}

_missing = [k for k, v in _required.items() if not v]
if _missing:
    raise RuntimeError(f"❌ Faltan variables en .env: {', '.join(_missing)}")
