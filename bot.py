import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from flask import Flask
from threading import Thread
import os
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE RENDER (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot de Tickets en línea ✅"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURACIÓN DEL BOT ---
# Activamos TODOS los permisos necesarios
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
intents.messages = True

bot = commands.Bot(command_prefix='(/)', intents=intents)

# --- CLASES DEL SISTEMA DE TICKETS (ORIGINALES) ---

class TicketModal(Modal, title="Abrir Nuevo Ticket de Soporte"):
    titulo = TextInput(label="¿En qué red social conociste el servidor?", placeholder="ser breve", max_length=80, required=True)
    descripcion = TextInput(label="¿Quién te invitó?", placeholder="ser breve", style=discord.TextStyle.long, max_length=80, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        rol_admin = discord.utils.get(guild.roles, name="Admin")
        rol_bot = discord.utils.get(guild.roles, name="bot")
        channel_name = f"ticket-{self.titulo.value.lower().replace(' ', '-')[:20]}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), 
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) 
        }
        if rol_admin: overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        if rol_bot: overwrites[rol_bot] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)

        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
        
        embed = discord.Embed(title=f"Nuevo Ticket: {self.titulo.value}", description=f"**Usuario:** {user.mention}\n**Invitado por:** {self.descripcion.value}", color=discord.Color.yellow())
        
        await ticket_channel.send(content=f"{user.mention} Bienvenido.", embed=embed, view=GestionTicketView(ticket_opener=user))
        await interaction.response.send_message(f"Canal creado: {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None) 
    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent_view:ticket_button")
    async def ticket_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal())

class GestionTicketView(View):
    def __init__(self, ticket_opener):
        super().__init__(timeout=None)
        self.ticket_opener = ticket_opener
    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar")
    async def cerrar_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Borrando canal...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

# --- EVENTOS ---
@bot.event
async def on_ready():
    print(f'✅ Bot listo: {bot.user.name}')
    if not hasattr(bot, 'persistent_views_added'):
        bot.add_view(TicketView())
        setattr(bot, 'persistent_views_added', True)
        async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        print(f"❌ Comando no encontrado: {ctx.message.content}")
    else:
        print(f"⚠️ Error detectado: {error}")

# --- COMANDOS ---
@bot.command()
@commands.has_permissions(administrator=True) 
async def enviarticket(ctx):
    embed = discord.Embed(title="Soporte", description="Haz clic abajo.", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

# --- EJECUCIÓN ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    keep_alive()
    bot.run(TOKEN)
