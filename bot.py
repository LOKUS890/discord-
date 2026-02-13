# VERSION 6.0 - OPTIMIZADA (SIN LAG / INTERACCIÓN FALLIDA)
import discord
from discord.ext import commands
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
def home(): return "Bot Online - Versión Veloz"

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
bot = commands.Bot(command_prefix='!', intents=intents)

# --- PANEL DE GESTIÓN ---
class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.green, custom_id="apr_v6")
    async def ap(self, it, b):
        # PRIMERO: Avisamos a Discord que estamos procesando (evita error 3 seg)
        await it.response.defer(ephemeral=True) 
        
        if it.user.id == self.opener.id:
            return await it.followup.send("❌ No puedes aprobarte a ti mismo.", ephemeral=True)
        
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.channel.send(f"✅ {self.opener.mention} aprobado por {it.user.mention}.")
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.red, custom_id="den_v6")
    async def den(self, it, b):
        await it.response.defer(ephemeral=True)
        
        if it.user.id == self.opener.id:
            return await it.followup.send("❌ Solo Staff puede denegar.", ephemeral=True)

        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.channel.send(f"❌ {self.opener.mention} denegado por {it.user.mention}.")
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Cerrar", style=discord.ButtonStyle.grey, custom_id="cls_v6")
    async def cl(self, it, b):
        await it.channel.delete()

# --- FORMULARIO Y TICKET ---
class TicketModal(Modal, title="Verificación"):
    respuesta = TextInput(label="¿Cómo nos conociste?", style=discord.TextStyle.long, required=True)

    async def on_submit(self, it: discord.Interaction):
        # Diferimos la respuesta aquí también
        await it.response.defer(ephemeral=True)
        
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        chan = await it.guild.create_text_channel(f"tkt-{it.user.name}", overwrites=overwrites)
        
        embed = discord.Embed(
            title="Nueva Solicitud", 
            description=f"**Usuario:** {it.user.mention}\n**Respuesta:** {self.respuesta.value}", 
            color=discord.Color.blue()
        )
        await chan.send(embed=embed, view=GestionTicketView(it.user))
        await it.followup.send(f"✅ Ticket creado en {chan.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_v6")
    async def b(self, it, bt):
        await it.response.send_modal(TicketModal())

# --- EVENTOS Y LISTA ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # Registro rápido en segundo plano
    asyncio.create_task(collection.update_one({"_id": str(msg.author.id)}, {"$set": {"last_seen": datetime.now()}}, upsert=True))
    await bot.process_commands(msg)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def listafantasmas(ctx):
    await ctx.send("🔎 Consultando inactivos...")
    limite = datetime.now() - timedelta(days=30)
    cursor = collection.find({"last_seen": {"$lt": limite}})
    inactivos = [f"<@{doc['_id']}>" async for doc in cursor]
    await ctx.send(f"👻 Inactivos: {', '.join(inactivos) if inactivos else 'Nadie'}")

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    await ctx.send("Inicia tu verificación aquí:", view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print("✅ Bot V6 Listo y Veloz")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
