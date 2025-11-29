FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .  # <-- ¡Esta línea funcionará ahora que el nombre es correcto!
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
