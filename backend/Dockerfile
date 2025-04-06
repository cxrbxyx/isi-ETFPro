FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear el directorio instance si no existe
RUN mkdir -p instance

# Variables de entorno para las APIs
ENV ALPHA_VANTAGE_API_KEY=""
ENV TIINGO_API_TOKEN=""

# Exponer puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python", "app.py"]