# Imagen base
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos del proyecto
COPY . .

# Instala las dependencias
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expone el puerto por defecto de FastAPI
EXPOSE 8000

# Comando para lanzar FastAPI con hot reload (quítalo en producción)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# # Usar una imagen base de Python oficial
# FROM python:3.11-slim

# # Establecer el directorio de trabajo en /app
# WORKDIR /app

# # Copiar el archivo de requerimientos e instalar las dependencias
# # Esto aprovecha el almacenamiento en caché de capas de Docker
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copiar el resto del código de la aplicación
# COPY ./app /app

# # Exponer el puerto en el que correrá la aplicación
# EXPOSE 8000

# # Comando para ejecutar la aplicación usando Uvicorn
# # --host 0.0.0.0 es necesario para que sea accesible desde fuera del contenedor
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
