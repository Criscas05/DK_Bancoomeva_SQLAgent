# app/azure_openai.py

import os
from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
import pandas as pd


def get_azure_openai_llm() -> AzureChatOpenAI:
    """
    Carga las credenciales de Azure OpenAI desde .env
    y retorna un objeto AzureChatOpenAI configurado.
    """
    load_dotenv()  
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_base = os.getenv("AZURE_OPENAI_ENDPOINT")  
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
    api_type = os.getenv("AZURE_OPENAI_API_TYPE", "azure")

    if not api_key or not api_base or not deployment_name:
        raise ValueError("Faltan variables de AzureOpenAI (api_key, endpoint, deployment_name)")

    llm = AzureChatOpenAI(
        api_key=api_key,
        azure_endpoint=api_base,
        openai_api_version=api_version,
        azure_deployment=deployment_name,
        temperature=0.0
    )

    return llm


def embeddings_generation(self, df: pd.DataFrame, columns: dict = None) -> pd.DataFrame:
    """
    Genera embeddings para las columnas especificadas de un DataFrame y asigna un ID único si no existe.

    :param df: DataFrame de pandas que contiene los datos a los cuales se les generarán embeddings.
    :param columns: Diccionario donde las claves son los nombres de las columnas originales y los valores 
                    son los nombres de las nuevas columnas donde se almacenarán los embeddings.
    :return: DataFrame con los embeddings generados y una columna 'id' única si no existía previamente.
    """
    
    embeddings = AzureOpenAIEmbeddings(
            api_key=self.api_key,
            model=self.model_name,
            azure_endpoint=self.endpoint, 
            openai_api_type="azure",
        )

    for cols_name, cols_name_embeddings in columns.items():
        # Generacion de embeddings para columnas de busqueda vectorial
        df[cols_name_embeddings] = df[cols_name].apply(lambda x: embeddings.embed_query(x))

    # Generar ID único si no existe
    if 'id' not in df.columns:
        df['id'] = range(1, len(df) + 1)
        df['id'] = df['id'].astype(str)
        
    return df

