# 1. Usa una imagen base de Python 3.10
FROM python:3.10-slim

# 2. Establece el directorio de trabajo
WORKDIR /app

# 3. Copia el archivo de requisitos e instálalos
# Cambia 'COPY requirements.txt .' a:
COPY ./requirements.txt . # <--- Aseguramos que busque en la raíz con ./
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia el resto del código
# Cambia 'COPY . .' a:
COPY . .

# 5. Comando de inicio
CMD ["python", "bot.py"]
