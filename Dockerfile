# Etapa 1: build del frontend
FROM node:20 AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend .
RUN npm run build

# Etapa 2: backend con Python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia backend
COPY app ./app

# copia el build del frontend en la ruta esperada
COPY --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 5173

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5173"]
