# ... (Código anterior) ...
WORKDIR /app
# 
# CAMBIA ESTA LÍNEA:
# COPY requirements.txt .  
#
# POR ESTA LÍNEA:
COPY ./requirements.txt . # <-- Usamos ruta relativa a la raíz para forzar la lectura.
RUN pip install --no-cache-dir -r requirements.txt
# ... (Código posterior) ...
