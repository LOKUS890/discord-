# VERSION 4.0 - CON RESPUESTA DE USUARIO Y 3 BOTONES
import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput 
import asyncio 
from datetime import datetime
import os
from flask import Flask
from threading import Thread
from motor.motor_asyncio import AsyncIOMotorClient

app = Flask('')
@app.get('/')
def home(): return "Bot Online - V4"

def keep_alive():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))).start()

MONGO_URI = os.getenv("MONGODB_URI")
cluster = AsyncIOMotorClient(MONGO_URI)
db = cluster["servidor_data"]
collection = db["actividad"]

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- PANEL DE GESTIÓN (BOTONES) ---
class GestionTicketView(View):
    def __init__(self, opener):
        super().__init__(timeout=None)
        self.opener = opener

    @discord.ui.button(label="Aprobar", style=discord.ButtonStyle.green, custom_id="apr_v4", emoji="✅")
    async def ap(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="Verificado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message(f"✅ {self.opener.mention} aprobado.", ephemeral=False)
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Denegar", style=discord.ButtonStyle.red, custom_id="den_v4", emoji="❌")
    async def den(self, it, b):
        rol = discord.utils.get(it.guild.roles, name="expulsado")
        if rol: await self.opener.add_roles(rol)
        await it.response.send_message(f"❌ {self.opener.mention} denegado.", ephemeral=False)
        await asyncio.sleep(3); await it.channel.delete()

    @discord.ui.button(label="Cerrar", style=discord.ButtonStyle.grey, custom_id="cls_v4", emoji="🔒")
    async def cl(self, it, b):
        await it.channel.delete()

# --- FORMULARIO (MODAL) ---
class TicketModal(Modal, title="Formulario de Verificación"):
    # Aquí definimos la pregunta
    respuesta = TextInput(
        label="¿Cómo nos conociste / Quién te invitó?", 
        placeholder="Escribe tu respuesta aquí...",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, it: discord.Interaction):
        overwrites = {
            it.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            it.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            it.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        chan = await it.guild.create_text_channel(f"tkt-{it.user.name}", overwrites=overwrites)
        
        # AQUÍ ESTÁ EL CAMBIO: Creamos un Embed que incluye la respuesta del usuario
        embed = discord.Embed(
            title="Nueva Solicitud de Verificación", 
            description=f"**Usuario:** {it.user.mention}\n\n**Respuesta del formulario:**\n> {self.respuesta.value}", 
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"ID del usuario: {it.user.id}")
        
        await chan.send(embed=embed, view=GestionTicketView(it.user))
        await it.response.send_message(f"✅ Tu ticket ha sido creado en {chan.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="main_v4")
    async def b(self, it, bt):
        # Llamamos al Modal que definimos arriba
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
    await ctx.send("Presiona el botón para iniciar:", view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"✅ Bot V4 Listo")

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv("DISCORD_TOKEN"))
