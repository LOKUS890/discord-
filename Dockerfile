FROM python:3.10-slim
WORKDIR /app
# CAMBIA la línea 'COPY requirements.txt .' por esta:
COPY ./requirements.txt ./ 
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
