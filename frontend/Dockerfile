# Usa una imagen base de Node
FROM node:18

# Crea el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia package.json y package-lock.json (mejor caché)
COPY package*.json ./

# Instala dependencias
RUN npm install

# Copia el resto del código
COPY . .

# Expone el puerto donde Vite corre en modo dev
EXPOSE 8501

# Comando de desarrollo
CMD ["npm", "run", "dev", "--", "--host"]

