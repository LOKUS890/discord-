FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .  # <-- Si el directorio raíz funciona, esto bastará
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
