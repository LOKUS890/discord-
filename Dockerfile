# Usa la imagen base de Python 3.10
FROM python:3.10-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de requisitos e instálalos
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código (incluyendo bot.py)
COPY . .

# Comando de inicio
CMD ["python", "bot.py"]
