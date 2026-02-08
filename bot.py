import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 

# --- AÑADIDOS PARA EL HOSTING 24/7 ---
from dotenv import load_dotenv
import os
from flask import Flask        # <--- NUEVO
from threading import Thread   # <--- NUEVO
# ------------------------------------

# --- CONFIGURACIÓN DEL SERVIDOR WEB (PARA KOYEB) ---
app = Flask('')

@app.get('!')
def home():
    return "¡Bot vivo y funcionando 24/7!"

def run_web_server():
    # Koyeb usa el puerto 8080 por defecto
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()
# ---------------------------------------------------

# --- 1. CONFIGURACIÓN DEL BOT Y INTENTS ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='/', intents=intents)

# ... (Aquí va todo tu código de Clases, Modals y Eventos que ya tenías) ...
# (He omitido el bloque central para que la respuesta no sea eterna, pero manténlo igual)

# -----------------------------------------------------------------------
# --- 5. EJECUTAR EL BOT -----------------------------------------------
# -----------------------------------------------------------------------

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") 

if TOKEN is None:
    print("\n\n❌ ERROR CRÍTICO: No se encontró la variable DISCORD_TOKEN.")
else:
    try:
        print("✅ Iniciando servidor de supervivencia...")
        keep_alive()  # <--- LANZAMOS EL SERVIDOR WEB AQUÍ
        
        print("✅ Token cargado con éxito. Iniciando bot...")
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ ERROR al iniciar el bot: {e}")



