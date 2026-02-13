import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput 
import asyncio 
from datetime import datetime
import os
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient

# --- SUPERVIVENCIA KOYEB ---
app = Flask('')
@app.get('/')
def home(): return "Bot Online - Protección Activa"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))).start()

# --- CONEXIÓN BASE DE DATOS ---
MONGO_URI = os.getenv("MONGODB_URI")
cluster = AsyncIOMotorClient(MONGO_URI)
db = cluster["servidor_data"]
collection = db["actividad"]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- PANEL DE GESTIÓN (LOS 3 BOTONES CON PROTECCIÓN) ---
class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener # Guardamos al usuario que creó el ticket

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.green, custom_id="apr_final", emoji="✅")
    async def ap(self, it, b):
        # SI EL USUARIO QUE PULSA ES EL MISMO QUE CREÓ EL TICKET, SE CANCELA
        if it.user.id == self.opener.id:
            return await it.response.send_message("❌ No puedes aprobar tu propia solicitud.", ephemeral=True)
        
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message(f"✅ {self.opener.mention} aprobado por {it.user.mention}.")
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.red, custom_id="den_final", emoji="❌")
    async def den(self, it, b):
        if it.user.id == self.opener.id:
            return await it.response.send_message("❌ Solo el Staff puede denegar esta solicitud.", ephemeral=True)

        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message(f"❌ {self.opener.mention} denegado por {it.user.mention}.")
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Cerrar", style=discord.ButtonStyle.grey, custom_id="cls_final", emoji="🔒")
    async def cl(self, it, b):
        # El botón de cerrar sí lo puede usar cualquiera
        await it.channel.delete()

# --- FORMULARIO Y TICKET ---
class TicketModal(Modal, title="Formulario de Verificación"):
    respuesta = TextInput(label="¿Cómo nos conociste?", style=discord.TextStyle.long, required=True)

    async def on_submit(self, it: discord.Interaction):
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        chan = await it.guild.create_text_channel(f"tkt-{it.user.name}", overwrites=overwrites)
        
        # EL EMBED AHORA SÍ MUESTRA LA RESPUESTA
        embed = discord.Embed(
            title="Nueva Solicitud", 
            description=f"**Usuario:** {it.user.mention}\n**Respuesta:** {self.respuesta.value}", 
            color=discord.Color.blue()
        )
        await chan.send(embed=embed, view=GestionTicketView(it.user))
        await it.response.send_message(f"✅ Ticket creado en {chan.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_final")
    async def b(self, it, bt):
        await it.response.send_modal(TicketModal())

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    try: await collection.update_one({"_id": str(msg.author.id)}, {"$set": {"last_seen": datetime.now()}}, upsert=True)
    except: pass
    await bot.process_commands(msg)

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    await ctx.send("Inicia tu verificación aquí:", view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print("✅ Bot Final con Seguridad de ID Activa")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
