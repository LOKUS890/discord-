import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient

# --- 1. SUPERVIVENCIA KOYEB (FLASK) ---
app = Flask('')
@app.get('/')
def home(): return "¡Bot Vitalicio Online!"

def keep_alive():
    # Escucha en el puerto 8080 para que Koyeb de el OK
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080))))
    t.start()

# --- 2. CONEXIÓN BASE DE DATOS ---
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

# --- 4. SISTEMA DE TICKETS (CON 3 BOTONES: APROBAR, DENEGAR, CERRAR) ---
class TicketModal(Modal, title="Formulario de Acceso"):
    red = TextInput(label="¿Cómo nos conociste?", placeholder="Ej: TikTok", required=True)
    async def on_submit(self, it: discord.Interaction):
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        chan = await it.guild.create_text_channel(f"tkt-{it.user.name}", overwrites=overwrites)
        await chan.send(f"Bienvenido {it.user.mention}\nRed: {self.red.value}", view=GestionTicketView(it.user))
        await it.response.send_message(f"Ticket creado: {chan.mention}", ephemeral=True)

class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="btn_apr")
    async def ap(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message("Usuario aprobado.", ephemeral=True)
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="❌ Denegar", style=discord.ButtonStyle.red, custom_id="btn_den")
    async def den(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message("Usuario denegado.", ephemeral=True)
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.grey, custom_id="btn_cl")
    async def cl(self, it, b): await it.channel.delete()

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_tkt")
    async def b(self, it, bt): await it.response.send_modal(TicketModal())

# --- 5. RASTREO Y REPORTE MENSUAL ---
async def registrar_actividad(uid):
    await collection.update_one({"_id": str(uid)}, {"$set": {"last_seen": datetime.now()}}, upsert=True)

@bot.event
async def on_message(msg):
    if not msg.author.bot: await registrar_actividad(msg.author.id)
    await bot.process_commands(msg)

@tasks.loop(hours=24)
async def informe_mensual():
    if datetime.now().day != 1: return 
    canal = discord.utils.get(bot.get_all_channels(), name="staff-logs")
    if not canal: return
    
    limite = datetime.now() - timedelta(days=30)
    cursor = collection.find({"last_seen": {"$lt": limite}})
    inactivos = [f"<@{doc['_id']}>" async for doc in cursor]
    
    if inactivos:
        await canal.send(f"📅 **Informe Mensual de Inactivos:**\n" + ", ".join(inactivos))

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    if not informe_mensual.is_running(): informe_mensual.start()
    print(f"🤖 Bot {bot.user.name} conectado.")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
