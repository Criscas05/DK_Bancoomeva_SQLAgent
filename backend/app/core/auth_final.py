# app/core/auth.py

import logging
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from app.core.config import settings
from app.core.middleware import AuthManager, User

logger = logging.getLogger("auth")
logging.basicConfig(level=logging.INFO)

# 1️⃣ Creamos una instancia única de AuthManager
auth_manager = AuthManager(settings.auth)

# 2️⃣ Dependency que valida el bearer token y devuelve un User
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer())
) -> User:
    """
    Extrae el 'access_token' del header Authorization,
    lo decodifica y valida, y devuelve un User.
    Si falla la validación, lanza HTTPException(401).
    """
    token = credentials.credentials
    try:
        user = await auth_manager.decode_user(token)
        return user
    except HTTPException as exc:
        # Puedes loguear el error si quieres
        logger.warning(f"[AUTH] Acceso denegado: {exc.detail}")
        # Re-lanzamos para que FastAPI devuelva 401
        raise

# 3️⃣ (Opcional) una función para inspeccionar claims sin verificar firma
def inspect_token(token: str) -> dict:
    """
    Para debugging: devuelve las claims sin validar la firma.
    """
    return auth_manager.inspect_token(token)
