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
def home(): return "Bot Online - V6 Speed"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))).start()

# --- CONEXIÓN BASE DE DATOS (ASYNC) ---
MONGO_URI = os.getenv("MONGODB_URI")
cluster = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = cluster["servidor_data"]
collection = db["actividad"]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- PANEL DE GESTIÓN (TICKETS) ---
class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.green, custom_id="apr_v6", emoji="✅")
    async def ap(self, it, b):
        # USAMOS DEFER PARA EVITAR "INTERACCIÓN FALLIDA"
        await it.response.defer(ephemeral=True)
        
        if it.user.id == self.opener.id:
            return await it.followup.send("❌ No puedes aprobarte a ti mismo.", ephemeral=True)
        
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.channel.send(f"✅ {self.opener.mention} aprobado por {it.user.mention}.")
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.red, custom_id="den_v6", emoji="❌")
    async def den(self, it, b):
        await it.response.defer(ephemeral=True)
        if it.user.id == self.opener.id:
            return await it.followup.send("❌ Solo Staff puede denegar.", ephemeral=True)

        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.channel.send(f"❌ {self.opener.mention} denegado por {it.user.mention}.")
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Cerrar", style=discord.ButtonStyle.grey, custom_id="cls_v6", emoji="🔒")
    async def cl(self, it, b):
        await it.channel.delete()

# --- FORMULARIO PERSONALIZADO ---
class TicketModal(Modal, title="Formulario de Verificación"):
    red_social = TextInput(label="¿En qué red social nos conociste?", placeholder="TikTok, Facebook...", required=True)
    invitado = TextInput(label="¿Quién te invitó?", placeholder="Nombre del usuario", required=True)

    async def on_submit(self, it: discord.Interaction):
        await it.response.defer(ephemeral=True) # Respuesta rápida
        
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        chan = await it.guild.create_text_channel(f"tkt-{it.user.name}", overwrites=overwrites)
        
        embed = discord.Embed(title="Nueva Solicitud", color=discord.Color.blue())
        embed.add_field(name="Usuario", value=it.user.mention)
        embed.add_field(name="Red Social", value=self.red_social.value)
        embed.add_field(name="Invitado por", value=self.invitado.value)
        
        await chan.send(embed=embed, view=GestionTicketView(it.user))
        await it.followup.send(f"✅ Ticket creado: {chan.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_v6")
    async def b(self, it, bt):
        await it.response.send_modal(TicketModal())

# --- RASTREO Y COMANDO DE LISTA ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # Registro en segundo plano para no dar lag al bot
    asyncio.create_task(collection.update_one({"_id": str(msg.author.id)}, {"$set": {"last_seen": datetime.now()}}, upsert=True))
    await bot.process_commands(msg)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def listafantasmas(ctx):
    """Muestra usuarios inactivos por más de 30 días"""
    await ctx.send("🔎 Buscando en la base de datos...")
    try:
        limite = datetime.now() - timedelta(days=30)
        cursor = collection.find({"last_seen": {"$lt": limite}})
        inactivos = [f"<@{doc['_id']}>" async for doc in cursor]
        
        if not inactivos:
            return await ctx.send("✅ No hay usuarios inactivos.")
        
        await ctx.send(f"👻 **Usuarios inactivos (+30 días):**\n{', '.join(inactivos[:20])}")
    except Exception as e:
        await ctx.send(f"❌ Error al conectar con MongoDB: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    await ctx.send("Pulsa para iniciar tu verificación:", view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print("✅ Bot V6 (Velocidad Máxima) Listo")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
