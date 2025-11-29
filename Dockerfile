# 1. Usa una imagen base de Python 3.10, lo que garantiza 'pip'
FROM python:3.10-slim

# 2. Establece el directorio de trabajo
WORKDIR /app

# 3. Copia el archivo de requisitos e instálalos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia el resto del código (incluyendo bot.py)
COPY . .

# 5. Comando de inicio
CMD ["python", "bot.py"]
