FROM python:3.10-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos el archivo de dependencias primero (mejor para la caché)
COPY requirements.txt .

# Instalamos las librerías
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos absolutamente todo el contenido de tu carpeta al contenedor
COPY . .

# Comando para arrancar el bot
CMD ["python", "bot.py"]
