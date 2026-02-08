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
        
        await ticket_channel.send(content=f"¡


