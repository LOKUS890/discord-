import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient # Importante para evitar el error de tu imagen

# --- 1. SUPERVIVENCIA KOYEB ---
app = Flask('')
@app.get('/')
def home(): return "¡Bot Online y Base de Datos Conectada!"

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080))))
    t.start()

# --- 2. CONEXIÓN BASE DE DATOS ASINCRÓNICA ---
# Esto corrige el error de "Ignoring exception in on_message"
MONGO_URI = os.getenv("MONGODB_URI")
cluster = AsyncIOMotorClient(MONGO_URI)
db = cluster["servidor_data"]
collection = db["actividad"]

# --- 3. CONFIGURACIÓN BOT ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
intents.presences = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 4. SISTEMA DE TICKETS ---
class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="btn_apr")
    async def ap(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message("Aprobado.", ephemeral=True)
        await asyncio.sleep(2); await it.channel.delete()

    @discord.ui.button(label="❌ Denegar", style=discord.ButtonStyle.red, custom_id="btn_den")
    async def den(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message("Denegado.", ephemeral=True)
        await asyncio.sleep(2); await it.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.grey, custom_id="btn_cl")
    async def cl(self, it, b): await it.channel.delete()

class TicketModal(Modal, title="Acceso"):
    red = TextInput(label="¿Cómo nos conociste?", required=True)
    async def on_submit(self, it: discord.Interaction):
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        chan = await it.guild.create_text_channel(f"tkt-{it.user.name}", overwrites=overwrites)
        await chan.send(f"Solicitud de {it.user.mention}", view=GestionTicketView(it.user))
        await it.response.send_message(f"Canal: {chan.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_tkt")
    async def b(self, it, bt): await it.response.send_modal(TicketModal())

# --- 5. RASTREO (CORREGIDO PARA EVITAR ERRORES) ---
async def registrar_actividad(uid):
    # Usamos await para que el bot no se trabe
    await collection.update_one(
        {"_id": str(uid)}, 
        {"$set": {"last_seen": datetime.now()}}, 
        upsert=True
    )

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # Registrar actividad sin bloquear el resto del bot
    await registrar_actividad(msg.author.id)
    # IMPORTANTE: Procesar comandos después de registrar
    await bot.process_commands(msg)

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"✅ Bot {bot.user.name} conectado y Healthy.")

# --- 6. COMANDOS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    await ctx.send("Haz clic abajo para iniciar la verificación:", view=TicketView())

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
