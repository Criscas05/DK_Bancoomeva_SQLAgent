from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from openai import AzureOpenAI
from langchain_community.callbacks import get_openai_callback
import os
from dotenv import load_dotenv, find_dotenv
import pandas as pd
from app import config


# Cargar variables desde el archivo .env
load_dotenv(find_dotenv())


class AzureOpenAIFunctions:
    """
    Esta clase encapsula la interacción con los servicios de Azure OpenAI,
    proporcionando funcionalidades avanzadas para el procesamiento de las conversaciones, 
    generación de embeddings y generación de respuestas.
    """


    def __init__(self) -> None:
        """
        Constructor de la clase.

        Inicializa las conexiones con los servicios de Azure OpenAI, incluyendo los modelos de lenguaje GPT-4o, GPT-o1
        y el servicio de embeddings.

        Variables de entorno utilizadas:
        - AZURE_OPENAI_ENDPOINT: URL del endpoint del servicio de OpenAI en Azure.
        - AZURE_OPENAI_API_KEY: Clave de autenticación para el servicio.
        - AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDINGS: Nombre del modelo de embeddings desplegado en Azure.
        - AZURE_OPENAI_API_VERSION_4o: Versión de la API para GPT-4o.
        - AZURE_OPENAI_API_VERSION_o1: Versión de la API para GPT-o1.

        Retorna:
        None
        """
        
        # Primero intentar cargar las variables de entorno
        self.endpoint = config.AZURE_OPENAI_ENDPOINT
        self.api_key = config.AZURE_OPENAI_API_KEY
        self.model_name_gpt_4o = config.AZURE_OPENAI_MODEL_NAME
        self.model_name = config.AZURE_OPENAI_EMBEDDING_NAME
        self.api_version_4o = config.AZURE_OPENAI_API_VERSION

        # Inicialización del modelo GPT-4o
        self.llm_4o = AzureChatOpenAI(
            azure_deployment=self.model_name_gpt_4o,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version_4o,
            temperature=0.4
        )
        # Cliente de respuesta de Azure OpenAI
        self.client_response = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version_4o,
        )

        # Inicialización del modelo de embeddings de Azure OpenAI
        self.embeddings = AzureOpenAIEmbeddings(
            api_key=self.api_key,
            model=self.model_name,
            azure_endpoint=self.endpoint, 
            openai_api_type="azure",
        )
    
    def embeddings_generation(self, df: pd.DataFrame, columns: dict = None) -> pd.DataFrame:
        """
        Genera embeddings para las columnas especificadas de un DataFrame y asigna un ID único si no existe.

        :param df: DataFrame de pandas que contiene los datos a los cuales se les generarán embeddings.
        :param columns: Diccionario donde las claves son los nombres de las columnas originales y los valores 
                        son los nombres de las nuevas columnas donde se almacenarán los embeddings.
        :return: DataFrame con los embeddings generados y una columna 'id' única si no existía previamente.
        """
        
        for cols_name, cols_name_embeddings in columns.items():
            # Generacion de embeddings para columnas de busqueda vectorial
            df[cols_name_embeddings] = df[cols_name].apply(lambda x: self.embeddings.embed_query(x))

        # Generar ID único si no existe
        if 'id' not in df.columns:
            df['id'] = range(1, len(df) + 1)
            df['id'] = df['id'].astype(str)
            
        return df
    
    def model_response(self,prompt_with_context) -> str:
        """
        Genera una respuesta basada en el prompt proporcionado.

        Parámetros
        -----------
        - prompt (str): El prompt.

        Return
        --------
        - str: La respuesta generada por el mmodelo de lenguaje.

        """

        chat_completion = self.client_response.chat.completions.create(
        model=self.llm_4o,
        messages=[{"role": "system", "content": prompt_with_context}],
        temperature=0.3,
        max_tokens=4000
        )

        response = chat_completion.choices[0].message.content
        
        return response
    
    def get_embedding(self, text: str) -> list[float]:
        """
        Genera un vector (embedding) para un texto dado usando el modelo de OpenAI.

        Args:
            text (str): El texto a vectorizar.
            client (openai.AzureOpenAI): El cliente de Azure OpenAI.

        Returns:
            list[float]: La representación vectorial del texto.
        """
        #embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        embedding = self.client_response.embeddings.create(input=[text], model=self.model_name).data[0].embedding
        return embedding