import discord
from discord.ext import commands, tasks
from discord.ui import View, Modal, TextInput 
import asyncio 
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient

# Supervivencia Koyeb
app = Flask('')
@app.get('/')
def home(): return "Bot Online"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))).start()

# Conexión a Base de Datos
MONGO_URI = os.getenv("MONGODB_URI")
cluster = AsyncIOMotorClient(MONGO_URI)
db = cluster["servidor_data"]
collection = db["actividad"]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
intents.presences = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- BOTONES DE TICKETS ---
class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="apr_btn")
    async def ap(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message("Aprobado", ephemeral=True)
        await asyncio.sleep(2); await it.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.grey, custom_id="cls_btn")
    async def cl(self, it, b): await it.channel.delete()

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_tkt")
    async def b(self, it, bt):
        modal = Modal(title="Verificación")
        modal.add_item(TextInput(label="¿Cómo nos conociste?"))
        async def on_submit(it_modal):
            overwrites = {it_modal.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                          it_modal.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                          it_modal.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
            chan = await it_modal.guild.create_text_channel(f"tkt-{it_modal.user.name}", overwrites=overwrites)
            await chan.send(f"Ticket de {it_modal.user.mention}", view=GestionTicketView(it_modal.user))
            await it_modal.response.send_message(f"Ticket: {chan.mention}", ephemeral=True)
        modal.on_submit = on_submit
        await it.response.send_modal(modal)

# --- COMANDOS Y REGISTRO ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # Intentamos registrar, pero si falla el enlace de Mongo, el comando SIGUE funcionando
    try:
        await collection.update_one({"_id": str(msg.author.id)}, {"$set": {"last_seen": datetime.now()}}, upsert=True)
    except:
        print("⚠️ Error de conexión a MongoDB. Revisa la variable en Koyeb.")
    
    await bot.process_commands(msg)

@bot.command()
async def listafantasmas(ctx):
    await ctx.send("🔎 Buscando usuarios inactivos en la base de datos...")
    try:
        limite = datetime.now() - timedelta(days=30)
        cursor = collection.find({"last_seen": {"$lt": limite}})
        inactivos = [f"<@{doc['_id']}>" async for doc in cursor]
        await ctx.send(f"Usuarios inactivos: {', '.join(inactivos) if inactivos else 'Ninguno'}")
    except:
        await ctx.send("❌ Error: No se pudo conectar a la base de datos. Verifica el enlace en Koyeb.")

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    await ctx.send("Presiona para iniciar verificación:", view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"✅ {bot.user.name} conectado.")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
