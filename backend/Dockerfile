# Usa una imagen ligera basada en Python 3.9
FROM python:3.9

# Evita que Python genere archivos pyc y usa salida sin buffer
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo
WORKDIR /app

# Copia solo requirements.txt primero para aprovechar la cache de Docker
COPY requirements.txt .

# Instala dependencias en un solo paso optimizado
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Crea un usuario no root por seguridad
# RUN useradd -m appuser
# USER appuser

# Expone el puerto de la aplicación
EXPOSE 8000

# Comando de ejecución
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]