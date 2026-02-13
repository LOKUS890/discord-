import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput 
import asyncio 
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from flask import Flask
from threading import Thread

# --- 1. SUPERVIVENCIA EN KOYEB (FLASK) ---
app = Flask('')

@app.get('/')
def home():
    return "¡Bot verificado y rastreador activo 24/7!"

def run_web_server():
    port = int(os.getenv("PORT", 8080)) # Puerto 8080 obligatorio en Koyeb
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.start()

# --- 2. CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
intents.presences = True # Necesario para ver si están online

bot = commands.Bot(command_prefix='!', intents=intents)

# Diccionario temporal para la actividad (Se borra si Koyeb reinicia)
last_seen_data = {}

# --- 3. LÓGICA DE TICKETS (FORMULARIO Y BOTONES) ---

class TicketModal(Modal, title="Formulario de Verificación"):
    red = TextInput(label="¿Red social?", placeholder="Ej: TikTok", required=True)
    invitado = TextInput(label="¿Quién te invitó?", placeholder="Nombre", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), 
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) 
        }
        ticket_channel = await guild.create_text_channel(f"ticket-{user.name}", overwrites=overwrites)
        embed = discord.Embed(title="Ticket Abierto", description=f"**Usuario:** {user.mention}\n**Red:** {self.red.value}\n**Invitado:** {self.invitado.value}", color=discord.Color.yellow())
        await ticket_channel.send(embed=embed, view=GestionTicketView(ticket_opener=user))
        await interaction.response.send_message(f"Canal: {ticket_channel.mention}", ephemeral=True)

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
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("⛔ Solo Staff.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="ticket_aprobado")
    async def aprobar(self, interaction: discord.Interaction, button: Button):
        rol = discord.utils.get(interaction.guild.roles, name="Verificado")
        if rol: await self.ticket_opener.add_roles(rol)
        await interaction.response.send_message("Aprobado.", ephemeral=True)
        await asyncio.sleep(3); await interaction.channel.delete()

    @discord.ui.button(label="❌ Denegar", style=discord.ButtonStyle.red, custom_id="ticket_denegado")
    async def denegar(self, interaction: discord.Interaction, button: Button):
        rol = discord.utils.get(interaction.guild.roles, name="expulsado")
        if rol: await self.ticket_opener.add_roles(rol)
        await interaction.response.send_message("Denegado.", ephemeral=True)
        await asyncio.sleep(3); await interaction.channel.delete()

    @discord.ui.button(label="🔒 Cerrar", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar")
    async def cerrar(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.delete()

# --- 4. RASTREADOR DE ACTIVIDAD E INFORME MENSUAL ---

def registrar(user_id):
    last_seen_data[str(user_id)] = datetime.now().isoformat()

@bot.event
async def on_message(message):
    if not message.author.bot: registrar(message.author.id)
    await bot.process_commands(message)

@bot.event
async def on_presence_update(before, after):
    if after.status != discord.Status.offline: registrar(after.id)

@tasks.loop(hours=24)
async def informe_mensual():
    await bot.wait_until_ready()
    if datetime.now().day != 1: return # Solo el día 1 de cada mes
    
    canal = discord.utils.get(bot.get_all_channels(), name="staff-logs")
    if not canal: return

    limite = datetime.now() - timedelta(days=30)
    inactivos = [f"<@{uid}>" for uid, fecha in last_seen_data.items() if datetime.fromisoformat(fecha) < limite]
    
    if inactivos:
        await canal.send(f"📅 **Informe Mensual de Inactivos:**\n" + ", ".join(inactivos))

# --- 5. COMANDOS Y EVENTOS FINALES ---

@bot.event
async def on_ready():
    bot.add_view(TicketView()) # Persistencia de botones
    if not informe_mensual.is_running(): informe_mensual.start()
    print(f'🤖 Bot {bot.user.name} online')

@bot.command()
@commands.has_permissions(administrator=True)
async def enviarticket(ctx):
    await ctx.send(view=TicketView())

@bot.command()
@commands.has_permissions(manage_channels=True)
async def listafantasmas(ctx):
    limite = datetime.now() - timedelta(days=30)
    fantasmas = [f"<@{uid}>" for uid, fecha in last_seen_data.items() if datetime.fromisoformat(fecha) < limite]
    await ctx.send(f"👻 Inactivos (+30 días): " + (", ".join(fantasmas) if fantasmas else "Ninguno"))

if __name__ == "__main__":
    load_dotenv()
    keep_alive() # Lanzamos Flask
    bot.run(os.getenv("DISCORD_TOKEN"))
