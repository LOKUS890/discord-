import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
import os
from dotenv import load_dotenv

# --- NUEVO: SERVIDOR WEB PARA RENDER ---
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot de Discord está en línea!"

def run_server():
    # Render usa la variable de entorno 'PORT' automáticamente
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()
# ---------------------------------------

# --- CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='(/)', intents=intents)

# --- CLASES DE TICKETS (Tu código original corregido) ---

class TicketModal(Modal, title="Abrir Nuevo Ticket de Soporte"):
    titulo = TextInput(
        label="¿En qué red social conociste el servidor?", 
        placeholder="Favor de ser breve",
        max_length=80,
        required=True,
    )

    descripcion = TextInput(
        label="¿Quién te invitó?", 
        placeholder="Favor de ser breve",
        style=discord.TextStyle.long, 
        max_length=80,
        required=True,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        rol_admin = discord.utils.get(guild.roles, name="Admin")
        rol_bot = discord.utils.get(guild.roles, name="bot")
        
        channel_name = f"ticket-{user.name[:15]}-{user.discriminator}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), 
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) 
        }

        if rol_admin: overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        embed_gestion = discord.Embed(
            title=f"Ticket Abierto",
            description=f"**Usuario:** {user.mention}\n**Red Social:** {self.titulo.value}\n**Invitado por:** {self.descripcion.value}", 
            color=discord.Color.yellow()
        )

        await ticket_channel.send(
            content=f"¡Nuevo Ticket de {user.mention}!",
            embed=embed_gestion, 
            view=GestionTicketView(ticket_opener=user)
        )
        
        await interaction.response.send_message(f"¡Ticket creado en {ticket_channel.mention}!", ephemeral=True)

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
        
    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="ticket_aprobado")
    async def aprobar_button(self, interaction: discord.Interaction, button: Button):
        rol_verificado = discord.utils.get(interaction.guild.roles, name="Verificado") 
        if rol_verificado and self.ticket_opener:
            await self.ticket_opener.add_roles(rol_verificado)
        
        await interaction.response.send_message("Aprobado. Borrando canal...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar")
    async def cerrar_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cerrando canal...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

# --- EVENTOS ---

@bot.event
async def on_ready():
    print(f'🤖 Bot conectado como: {bot.user.name}')
    if not hasattr(bot, 'persistent_views_added'):
        bot.add_view(TicketView())
        setattr(bot, 'persistent_views_added', True)

@bot.command()
@commands.has_permissions(administrator=True) 
async def enviarticket(ctx):
    embed = discord.Embed(title="Panel de Tickets", description="Haz clic abajo para abrir un ticket.", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

# --- INICIO ---

if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    
    if TOKEN:
        # Iniciamos el servidor web antes que el bot
        keep_alive() 
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Falta el TOKEN en las variables de entorno.")
