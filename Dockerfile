# 1. Usa una imagen base de Python 3.10
# Esto garantiza que el comando 'pip' exista.
FROM python:3.10-slim

# 2. Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copia el archivo de requisitos
# Este paso copia tu requirements.txt
COPY requirements.txt .

# 4. Instala las dependencias (el comando que fallaba antes)
# --no-cache-dir asegura una construcción limpia
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia todo tu código restante (bot.py, etc.)
COPY . .

# 6. Comando para ejecutar el bot (lo que estaba en railway.toml)
# Ejecuta el script de inicio
CMD ["python", "bot.py"]
