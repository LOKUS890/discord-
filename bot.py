import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread

# --- 1. CONFIGURACIÓN DEL SERVIDOR WEB (PARA KOYEB) ---
# Esto es vital para que Koyeb vea al bot como "Healthy"
app = Flask('')

@app.get('/')
def home():
    return "¡Bot vivo y funcionando 24/7!"

def run_web_server():
    # Usamos el puerto 8080 que configuraste en Koyeb
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# --- 2. CONFIGURACIÓN DEL BOT Y INTENTS ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

# Prefijo '!' para evitar el error "Command not found" de las capturas
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. CLASES DE MODALS Y VISTAS (LÓGICA DE TICKETS) ---

class TicketModal(Modal, title="Abrir Nuevo Ticket de Soporte"):
    # Formulario que viste en tu código principal
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
        
        # Roles necesarios para los permisos del canal
        rol_admin = discord.utils.get(guild.roles, name="Admin")
        
        # Crear canal privado para el ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), 
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) 
        }

        if rol_admin:
            overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        ticket_channel = await guild.create_text_channel(f"ticket-{user.name}", overwrites=overwrites)

        # Embed con la información que el usuario llenó en el Modal
        embed = discord.Embed(
            title="Ticket Abierto",
            description=f"**Usuario:** {user.mention}\n**Red:** {self.red_social.value}\n**Invitado por:** {self.invitado_por.value}", 
            color=discord.Color.yellow()
        )
        
        # Enviamos el panel con los 3 botones: Aprobar, Denegar y Cerrar

