import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB (PARA KOYEB) ---
# Esto evita el error de "Service degraded" al responder en el puerto 8080
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

# --- 2. CONFIGURACIÓN DEL SERVIDOR DE DISCORD ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

# Usamos el prefijo '!' para que el comando sea fácil de ejecutar
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. CLASES DE MODALS Y VISTAS (LÓGICA DE TICKETS) ---

class TicketModal(Modal, title="Abrir Nuevo Ticket de Soporte"):
    red_social = TextInput(
        label="¿En qué red social conociste el servidor?", 
        placeholder="Ej: TikTok, Instagram...",
        max_length=80,
        required=True,
    )

    invitado_por = TextInput(
        label="¿Quién te invitó?", 
        placeholder="Nombre del usuario",
        style=discord.TextStyle.long, 
        max_length=80,
        required=True,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        
        rol_admin = discord.utils.get(guild.roles, name="Admin")
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), 
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) 
        }

        if rol_admin:
            overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        ticket_channel = await guild.create_text_channel(f"ticket-{user.name}", overwrites=overwrites)

        embed = discord.Embed(
            title="Ticket Abierto",
            description=f"**Usuario:** {user.mention}\n**Red:** {self.red_social.value}\n**Invitado por:** {self.invitado_por.value}", 
            color=discord.Color.yellow()
        )
        
        # Aquí enviamos la vista que contiene los 3 botones: Aprobar, Denegar y Cerrar
        await ticket_channel.send(
            content=f"¡Nuevo Ticket de {user.mention}!", 
            embed=embed, 
            view=GestionTicketView(ticket_opener=user)
        )
        await interaction.response.send_message(f"¡Ticket creado! Ve a {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    """Botón inicial para abrir el ticket"""
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent:ticket_button")
    async def ticket_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal())

class GestionTicketView(View):
    """Botones dentro del canal del ticket (Aprobar, Denegar, Cerrar)"""
    def __init__(self, ticket_opener):
        super().__init__(timeout=None)
        self.ticket_opener = ticket_opener
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Solo permite que el Staff (con gestionar canales) use Aprobar/Denegar
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("⛔ Solo el staff puede usar estos botones.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="ticket_aprobado")
    async def aprobar_button(self, interaction: discord.Interaction, button: Button):
        rol_verificado = discord.utils.get(interaction.guild.roles, name="Verificado")
        if rol_verificado and self.ticket_opener:
            await self.ticket_opener.add_roles(rol_verificado)
            await interaction.response.send_message(f"✅ Usuario verificado. El canal se borrará en breve.", ephemeral=True)
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="❌ Denegar", style=discord.ButtonStyle.red, custom_id="ticket_denegado")
    async def denegar_button(self, interaction: discord.Interaction, button: Button):
        rol_expulsado = discord.utils.get(interaction.guild.roles, name="expulsado")
        if rol_expulsado and self.ticket_opener:
            await self.ticket_opener.add_roles(rol_expulsado)
            await interaction.response.send_message(f"❌ Ticket denegado. El canal se borrará en breve.", ephemeral=True)
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar")
    async def cerrar_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cerrando ticket...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

# --- 4. EVENTOS Y COMANDOS ---

@bot.event
async def on_ready():
    print(f'🤖 Bot conectado como: {bot.user.name}')
    # Registramos la vista para que el botón de 'Crear Ticket' funcione siempre
    bot.add_view(TicketView())
    print('✅ Sistema de tickets y botones persistentes cargados.')

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    embed = discord.Embed(
        title="Sistema de Soporte 🎫", 
        description="Presiona el botón para abrir un ticket de verificación.", 
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

# --- 5. EJECUCIÓN ---

if __name__ == "__main__":
    load_dotenv()
    keep_alive() # Inicia el servidor Flask para Koyeb
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ ERROR: No se encontró DISCORD_TOKEN.")
