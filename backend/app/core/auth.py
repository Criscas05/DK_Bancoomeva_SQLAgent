# app/core/auth.py

from fastapi import Request, HTTPException, status
from jose import jwt
import requests
from functools import lru_cache
from typing import Dict

from os import getenv
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = getenv("AZURE_TENANT_ID")
CLIENT_ID = getenv("AZURE_CLIENT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
JWKS_URL = f"{AUTHORITY}/discovery/v2.0/keys"
AUDIENCE = CLIENT_ID

@lru_cache()
def get_jwks():
    try:
        response = requests.get(JWKS_URL)
        response.raise_for_status()
        return response.json()
    except Exception:
        raise HTTPException(status_code=500, detail="Error obteniendo claves públicas de Azure")

def get_public_key(kid: str):
    for key in get_jwks()["keys"]:
        if key["kid"] == kid:
            return key
    return None

def verify_token(token: str) -> Dict:
    try:
        headers = jwt.get_unverified_header(token)
        key = get_public_key(headers["kid"])

        if not key:
            raise HTTPException(status_code=401, detail="Clave pública no encontrada")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=f"{AUTHORITY}/v2.0"
        )

        return {
            "user_id": payload.get("sub"),  # o payload["oid"] si se prefiere ese ID
            "email": payload.get("preferred_username", ""),
            "name": payload.get("name", ""),
            "roles": payload.get("roles", [])
        }
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

async def get_current_user(request: Request) -> Dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Encabezado Authorization inválido o ausente")

    token = auth_header.split(" ")[1]
    return verify_token(token)
