import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput 
import asyncio 
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient

# --- SUPERVIVENCIA KOYEB ---
app = Flask('')
@app.get('/')
def home(): return "Bot Online - V9 Final"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))).start()

# --- CONEXIÓN BASE DE DATOS ---
# Usamos un timeout corto para que el bot no se congele esperando a MongoDB
MONGO_URI = os.getenv("MONGODB_URI")
cluster = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=3000)
db = cluster["servidor_data"]
collection = db["actividad"]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- PANEL DE GESTIÓN (BOTONES COMPLETOS) ---
class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.green, custom_id="apr_v9", emoji="✅")
    async def ap(self, it, b):
        await it.response.defer(ephemeral=True) # Evita "Interacción fallida"
        if it.user.id == self.opener.id:
            return await it.followup.send("❌ No puedes aprobarte a ti mismo.", ephemeral=True)
        
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.channel.send(f"✅ {self.opener.mention} aprobado por {it.user.mention}.")
        await asyncio.sleep(2); await it.channel.delete()

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.red, custom_id="den_v9", emoji="🚫")
    async def den(self, it, b):
        await it.response.defer(ephemeral=True)
        if it.user.id == self.opener.id:
            return await it.followup.send("❌ Solo Staff puede denegar.", ephemeral=True)

        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.channel.send(f"❌ {self.opener.mention} denegado por {it.user.mention}.")
        await asyncio.sleep(2); await it.channel.delete()

    @discord.ui.button(label="Cerrar", style=discord.ButtonStyle.grey, custom_id="cls_v9", emoji="🔒")
    async def cl(self, it, b):
        await it.channel.delete()

# --- FORMULARIO ---
class TicketModal(Modal, title="Formulario de Verificación"):
    red = TextInput(label="¿En qué red social nos conociste?", required=True)
    inv = TextInput(label="¿Quién te invitó?", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True)
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        chan = await it.guild.create_text_channel(f"tkt-{it.user.name}", overwrites=overwrites)
        embed = discord.Embed(title=f"Ticket de {it.user.name}", color=discord.Color.blue())
        embed.add_field(name="Red Social", value=self.red.value)
        embed.add_field(name="Invitado por", value=self.inv.value)
        
        await chan.send(embed=embed, view=GestionTicketView(it.user))
        await it.followup.send(f"✅ Ticket creado: {chan.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_v9")
    async def b(self, it, bt):
        await it.response.send_modal(TicketModal())

# --- RASTREO Y LISTA ---
async def registrar_seguro(uid):
    """Evita errores de TypeError y bloqueos"""
    try:
        await collection.update_one({"_id": str(uid)}, {"$set": {"last_seen": datetime.now()}}, upsert=True)
    except:
        pass

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    bot.loop.create_task(registrar_seguro(msg.author.id))
    await bot.process_commands(msg)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def listafantasmas(ctx):
    """Muestra nombres. Si la DB falla, avisa de forma limpia"""
    await ctx.send("🔎 Consultando base de datos...")
    try:
        limite = datetime.now() - timedelta(days=30)
        cursor = collection.find({"last_seen": {"$lt": limite}})
        inactivos = [f"<@{doc['_id']}>" async for doc in cursor]
        
        if not inactivos:
            return await ctx.send("✅ No hay usuarios registrados como inactivos.")
        
        await ctx.send(f"👻 **Usuarios inactivos:**\n{', '.join(inactivos)}")
    except Exception:
        await ctx.send("⚠️ La base de datos no responde actualmente. Inténtalo en unos minutos.")

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    await ctx.send("Presiona el botón para abrir un ticket:", view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print("✅ Bot V9 Listo y Completo")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
