#!/bin/bash

# Nombre de la imagen
IMAGE_NAME="bancoomeva:latest"

echo "🔨 Construyendo la imagen Docker..."
docker build -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
  echo "❌ Error al construir la imagen. Abortando."
  exit 1
fi

echo "🚀 Ejecutando el contenedor..."
docker run --rm -it -p 5173:5173/tcp $IMAGE_NAME
