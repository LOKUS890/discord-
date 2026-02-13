import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from datetime import datetime, timedelta
import os
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient # Para la base de datos
from dotenv import load_dotenv

# --- 1. SUPERVIVENCIA KOYEB (KEEP ALIVE) ---
app = Flask('')
@app.get('/')
def home(): return "Bot Online 24/7"

def keep_alive():
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080))))
    t.start()

# --- 2. CONFIGURACIÓN Y BASE DE DATOS ---
load_dotenv()
MONGO_URI = os.getenv("MONGODB_URI")
cluster = AsyncIOMotorClient(MONGO_URI)
db = cluster["servidor_data"]
collection = db["actividad"]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. CLASES DE TICKETS (TU ESTRUCTURA ORIGINAL MEJORADA) ---

class TicketModal(Modal, title="Abrir Nuevo Ticket de Soporte"):
    titulo = TextInput(label="¿En qué red social nos conociste?", placeholder="Ej: TikTok", max_length=80, required=True)
    descripcion = TextInput(label="¿Quién te invitó?", placeholder="Nombre del usuario", style=discord.TextStyle.long, max_length=80, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        
        # Definir roles
        rol_admin = discord.utils.get(guild.roles, name="Admin")
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        if rol_admin: overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel_name = f"ticket-{user.name[:10]}-{user.discriminator}"
        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        embed = discord.Embed(title=f"Ticket de {user.name}", color=discord.Color.yellow())
        embed.add_field(name="Red Social", value=self.titulo.value)
        embed.add_field(name="Invitado por", value=self.descripcion.value)
        
        await ticket_channel.send(f"🔔 {rol_admin.mention if rol_admin else ''} ¡Nuevo ticket!", embed=embed, view=GestionTicketView(ticket_opener=user))
        await interaction.response.send_message(f"Ticket creado en {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent:ticket")
    async def ticket_button(self, it, bt): await it.response.send_modal(TicketModal())

class GestionTicketView(View):
    def __init__(self, ticket_opener):
        super().__init__(timeout=None)
        self.opener = ticket_opener

    async def interaction_check(self, it: discord.Interaction) -> bool:
        if it.data.get('custom_id') == 'ticket_cerrar': return True
        if not it.user.guild_permissions.manage_channels:
            await it.response.send_message("⛔ Solo Staff puede usar esto.", ephemeral=True)
            return False
        if it.user.id == self.opener.id:
            await it.response.send_message("❌ No puedes gestionarte a ti mismo.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="ticket_aprobado")
    async def aprobar(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message(f"✅ {self.opener.mention} verificado.")
        await asyncio.sleep(5); await it.channel.delete()

    @discord.ui.button(label="❌ Denegar", style=discord.ButtonStyle.red, custom_id="ticket_denegado")
    async def denegar(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message(f"❌ {self.opener.mention} denegado.")
        await asyncio.sleep(5); await it.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar")
    async def cerrar(self, it, b):
        await it.channel.delete()

# --- 4. RASTREO DE ACTIVIDAD (MONGODB) ---

async def registrar_actividad(uid):
    await collection.update_one({"_id": str(uid)}, {"$set": {"last_seen": datetime.now()}}, upsert=True)

@bot.event
async def on_message(msg):
    if not msg.author.bot:
        await registrar_actividad(msg.author.id)
    await bot.process_commands(msg)

# --- 5. COMANDOS ---

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    embed = discord.Embed(title="Verificación", description="Pulsa para iniciar", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

@bot.command()
@commands.has_permissions(manage_channels=True)
async def listafantasmas(ctx):
    """Muestra los usuarios que no han hablado en los últimos 30 días."""
    await ctx.send("🔎 Consultando base de datos de actividad...")
    limite = datetime.now() - timedelta(days=30)
    
    # Buscamos en MongoDB usuarios cuya última actividad sea anterior a 30 días
    cursor = collection.find({"last_seen": {"$lt": limite}})
    inactivos = []
    async for doc in cursor:
        inactivos.append(f"<@{doc['_id']}>")

    if not inactivos:
        return await ctx.send("✅ Todos los usuarios registrados han estado activos este mes.")
    
    # Dividir el mensaje si son muchos usuarios
    msg = "👻 **Usuarios inactivos (+30 días):**\n" + ", ".join(inactivos)
    if len(msg) > 2000:
        await ctx.send(msg[:1990] + "...")
    else:
        await ctx.send(msg)

# --- 6. INICIO ---

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f'🤖 {bot.user.name} conectado.')

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))

