from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from openai import AzureOpenAI
from langchain_community.callbacks import get_openai_callback
import os
from dotenv import load_dotenv, find_dotenv
import time
import logging
import pandas as pd


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
        - AZURE_OPENAI_DEPLOYMENT_NAME_GPT_4o: Nombre del modelo GPT-4o desplegado en Azure.
        - AZURE_OPENAI_DEPLOYMENT_NAME_GPT_o1: Nombre del modelo GPT-o1 desplegado en Azure.
        - AZURE_OPENAI_API_VERSION_4o: Versión de la API para GPT-4o.
        - AZURE_OPENAI_API_VERSION_o1: Versión de la API para GPT-o1.

        Retorna:
        None
        """
        
        # Primero intentar cargar las variables de entorno
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.model_name = os.getenv("EMBEDDING_NAME")
        self.model_name_gpt_4o = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.api_version_4o = os.getenv("AZURE_OPENAI_API_VERSION")

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

        self.models = {
            "gpt-4o": self.llm_4o,
        }

        
    # Función para manejar reintentos
    def invoke_with_retry(self, chain, inputs: dict, retries: int = 8, delay: int = 2) -> tuple[str, any]:
        """
        Invoca una cadena de procesamiento con reintentos en caso de error.

        Parámetros:
        - chain: Objeto que representa la cadena de procesamiento a invocar.
        - inputs (dict): Diccionario con los datos de entrada para la cadena.
        - retries (int, opcional): Número máximo de intentos en caso de fallo (por defecto 8).
        - delay (int, opcional): Tiempo en segundos entre intentos (por defecto 2).

        Retorna:
        - tuple:
            - str: Texto de la respuesta generada si el proceso tiene éxito.
            - any: Objeto de callback con métricas de la ejecución o None si falla.
        """
        for i in range(retries):
            try:
                # Intentar invocar la cadena de procesamiento con callback de OpenAI
                with get_openai_callback() as cb:
                    response = chain.invoke(inputs)["text"]
                
                # Validar que la respuesta tenga al menos 1000 caracteres
                if len(response) < 1000:
                    raise ValueError("La respuesta es menor que 1000 caracteres")
                
                return response, cb  # Retorna la respuesta y el callback si tiene éxito

            except Exception as e:
                print(f"Intento {i + 1} fallido: {e}")
                time.sleep(delay)  # Espera antes de reintentar

        # Si falla después de todos los intentos, devuelve el texto original y None
        print(f"Fallo después de {retries} reintentos.")
        return inputs["text"], None
    
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
    
    
    def load_model(self, model_name: str):
        try:
            return self.models[model_name]
        except AttributeError as e:
            print(f"Model not initialized: {e}")
            return e