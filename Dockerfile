# ... (Código anterior) ...
WORKDIR /app

# 3. Copia el archivo de requisitos e instálalos
# Cambia 'COPY requirements.txt .' a:
COPY discord-/requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia el resto del código
# Cambia 'COPY . .' a:
COPY discord-/ .

# 5. Comando de inicio
# Cambia 'CMD ["python", "bot.py"]' a:
CMD ["python", "bot.py"] # <--- Este debe seguir igual si bot.py está en la raíz del contenedor (/app)
