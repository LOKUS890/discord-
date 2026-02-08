import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB (PARA KOYEB) ---
app = Flask('')

@app.get('/')
def home():
    return "¡Bot vivo y funcionando 24/7!"

def run_web_server():
    # Koyeb usa el puerto 8080 por defecto
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# --- 2. CONFIGURACIÓN DEL BOT Y INTENTS ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

# He cambiado el prefijo a '!' para evitar errores de lectura
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. CLASES DE MODALS Y VISTAS ---

class TicketModal(Modal, title="Abrir Nuevo Ticket de Soporte"):
    titulo = TextInput(
        label="¿En qué red social conociste el servidor?", 
        placeholder="favor de ser breve",
        max_length=80,
        required=True,
    )

    descripcion = TextInput(
        label="¿Quién te invitó?", 
        placeholder="favor de ser breve",
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

        if rol_admin:
            overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)

        embed_gestion = discord.Embed(
            title=f"Ticket Abierto",
            description=f"**Usuario:** {user.mention}\n**Red:** {self.titulo.value}\n**Invitado por:** {self.descripcion.value}", 
            color=discord.Color.yellow()
        )
        
        await ticket_channel.send(content=f"¡Nuevo Ticket de {user.mention}!", embed=embed_gestion, view=GestionTicketView(ticket_opener=user))
        await interaction.response.send_message(f"Ticket creado en {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent:ticket_button")
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
            await interaction.response.send_message(f"Usuario verificado. Cerrando...", ephemeral=True)
            await asyncio.sleep(5)
            await interaction.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar")
    async def cerrar_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cerrando canal...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

# --- 4. EVENTOS Y COMANDOS ---

@bot.event
async def on_ready():
    print(f'🤖 Bot conectado como: {bot.user.name}')
    bot.add_view(TicketView())
    print('✅ Sistema de tickets activado.')

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    embed = discord.Embed(title="Soporte", description="Haz clic abajo para abrir un ticket", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

# --- 5. EJECUCIÓN ---

if __name__ == "__main__":
    load_dotenv()
    keep_alive() # Esto arranca Flask para Koyeb
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: No hay TOKEN.")
