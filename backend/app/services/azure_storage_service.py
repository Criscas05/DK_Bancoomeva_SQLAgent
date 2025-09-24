import os
import io
import pandas as pd
from azure.storage.blob.aio import BlobServiceClient
from app import config
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from urllib.parse import urlparse

class AzureStorageService:
    def __init__(self):

        if not config.AZURE_STORAGE_SAS_TOKEN or not config.AZURE_STORAGE_ACCOUNT_URL or not config.AZURE_STORAGE_CONTAINER_NAME:
            raise ValueError("El SAS Token, la url de la cuenta y el contenedor deben estar configurados.")
        
        # Normalizar account_url y SAS para evitar URIs inválidas
        raw_account_url = config.AZURE_STORAGE_ACCOUNT_URL.strip()
        raw_sas = (config.AZURE_STORAGE_SAS_TOKEN or "").strip()

        parsed = urlparse(raw_account_url)
        # Tomar solo esquema + host para la cuenta (sin ruta ni query)
        base_account_url = f"{parsed.scheme}://{parsed.netloc}".rstrip('/')

        # Si la URL tenía query SAS y no se proporcionó por separado, la usa
        if parsed.query and not raw_sas:
            raw_sas = parsed.query

        self.account_url = base_account_url
        self.sas_token = raw_sas
        # Separar contenedor y prefijo de ruta si el usuario provee "contenedor/ruta/..."
        container_and_maybe_prefix = config.AZURE_STORAGE_CONTAINER_NAME.strip('/').split('/', 1)
        self.container_name = container_and_maybe_prefix[0]
        inferred_prefix = container_and_maybe_prefix[1] if len(container_and_maybe_prefix) > 1 else ""

        # Prefijo final: el de ENV dedicado tiene prioridad, si no, inferido desde el contenedor
        self.blob_prefix = (config.AZURE_STORAGE_BLOB_PREFIX or inferred_prefix).strip('/')

        # Crear URL base al contenedor con SAS
        self.blob_service_client = BlobServiceClient(account_url=self.account_url, credential=self.sas_token)
        
        print("Servicio de Azure Storage inicializado.")

    async def initialize_container(self):
        """Asegura que el contenedor de blobs exista, solo si se usan claves completas."""
        if not self.sas_token:
            # Solo intentamos validar si tenemos una clave con permisos elevados
            try:
                container_client = self.blob_service_client.get_container_client(self.container_name)
                await container_client.get_container_properties()
                print(f"Contenedor de Storage '{self.container_name}' encontrado.")
            except ResourceNotFoundError:
                print(f"Contenedor '{self.container_name}' no existe y no se puede crear con SAS token.")
            except Exception as e:
                print(f"Error al validar contenedor de Storage: {e}")
        else:
            print("⚠️ Saltando validación de contenedor porque se usa SAS token sin permisos elevados.")

    async def upload_query_results(self, df: pd.DataFrame, blob_name: str) -> str:
        """
        Convierte un DataFrame de Pandas a CSV, lo sube a Azure Blob Storage
        y devuelve la URL del blob.
        """
        try:
            # Convertir DataFrame a CSV en un buffer en memoria
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8')
            csv_data = output.getvalue().encode('utf-8')
            output.close()

            # Incorporar prefijo si existe
            effective_blob_name = f"{self.blob_prefix}/{blob_name}".strip('/') if self.blob_prefix else blob_name
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=effective_blob_name)
            await blob_client.upload_blob(csv_data, overwrite=True)
            print(f"Archivo CSV '{blob_name}' subido exitosamente a Azure Storage.")

            # Construir URL pública del blob evitando duplicar '?'
            sas = self.sas_token.lstrip('?') if self.sas_token else ''
            blob_url = f"{self.account_url}/{self.container_name}/{effective_blob_name}{('?' + sas) if sas else ''}"

            # Devolver la URL del archivo subido
            return blob_url
        except Exception as e:
            print(f"Error al subir el archivo CSV a Azure Storage: {e}")
            raise