import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 

# --- NUEVOS AÑADIDOS PARA RENDER (KEEP ALIVE) ---
from flask import Flask
from threading import Thread
import os
from dotenv import load_dotenv

# Creamos una pequeña app de Flask para que Render no apague el bot
app = Flask('')

@app.route('/')
def home():
    return "¡El bot de tickets está activo!"

def run():
    # Render usa el puerto que le asigne el sistema
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------------------

# --- 1. CONFIGURACIÓN DEL BOT Y INTENTS ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='(/)', intents=intents)

# -----------------------------------------------------------------------
# --- 2. CLASES DE MODALS Y VISTAS (BOTONES) ----------------------------
# -----------------------------------------------------------------------

# CLASE 2.1: MODAL (FORMULARIO DE PREGUNTAS)
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
        
        channel_name = f"ticket-{self.titulo.value.lower().replace(' ', '-')[:20]}-{user.discriminator}"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False), 
            user: discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True,
                manage_channels=False, 
                manage_messages=False,
                add_reactions=False
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) 
        }

        if rol_admin:
            overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        if rol_bot:
            overwrites[rol_bot] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)

        ticket_channel = await guild.create_text_channel(
            channel_name, 
            overwrites=overwrites, 
            category=None,
            topic=f"Ticket de {user.name}: {self.titulo.value}"
        )

        embed_gestion = discord.Embed(
            title=f"Ticket Abierto: {self.titulo.value}",
            description=f"**Usuario:** {user.mention}\n**Red Social:** {self.titulo.value}\n**Invitado por:** {self.descripcion.value}", 
            color=discord.Color.yellow()
        )
        embed_gestion.set_footer(text=f"ID de Usuario: {user.id}")

        menciones_texto = ""
        if rol_admin: 
            menciones_texto += f"{rol_admin.mention} "
        if rol_bot: 
            menciones_texto += f"{rol_bot.mention} "
        
        await ticket_channel.send(
            content=f"{menciones_texto} **¡Nuevo Ticket de {user.mention} Abierto!**",
            embed=embed_gestion, 
            view=GestionTicketView(ticket_opener=user)
        )
        
        await interaction.response.send_message(f"¡Tu ticket ha sido creado en {ticket_channel.mention}!", ephemeral=True)


# CLASE 2.2: BOTÓN PRINCIPAL
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent_view:ticket_button")
    async def ticket_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal())


# CLASE 2.3: BOTONES DE GESTIÓN
class GestionTicketView(View):
    def __init__(self, ticket_opener):
        super().__init__(timeout=None)
        self.ticket_opener = ticket_opener
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        is_staff = interaction.user.guild_permissions.manage_channels
        if interaction.data.get('custom_id') == 'ticket_cerrar':
            return True
        if not is_staff:
            await interaction.response.send_message("⛔ Solo el staff de gestión puede usar los botones.", ephemeral=True)
            return False
        return True
        
    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="ticket_aprobado")
    async def aprobar_button(self, interaction: discord.Interaction, button: Button):
        rol_verificado = discord.utils.get(interaction.guild.roles, name="Verificado") 
        aprobacion_msg = ""
        
        if rol_verificado:
            try:
                await self.ticket_opener.add_roles(rol_verificado)
                aprobacion_msg = f"✅ Rol **{rol_verificado.name}** otorgado a {self.ticket_opener.mention}."
            except discord.Forbidden:
                aprobacion_msg = "❌ Error de Permiso: El bot está por debajo del rol en la jerarquía."
            except Exception as e:
                aprobacion_msg = f"❌ Error: {e}"
        else:
            aprobacion_msg = "⚠️ Rol 'Verificado' no encontrado."

        await interaction.message.edit(content=f"✅ Ticket **APROBADO** por {interaction.user.mention}. {aprobacion_msg}", view=None)
        await interaction.response.send_message(f"Cerrando en 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()
        
    @discord.ui.button(label="❌ Denegar", style=discord.ButtonStyle.red, custom_id="ticket_denegado")
    async def denegar_button(self, interaction: discord.Interaction, button: Button):
        rol_expulsado = discord.utils.get(interaction.guild.roles, name="expulsado")
        denegacion_msg = ""
        
        if rol_expulsado:
            try:
                await self.ticket_opener.add_roles(rol_expulsado)
                denegacion_msg = f"⛔ Rol **{rol_expulsado.name}** otorgado."
            except discord.Forbidden:
                denegacion_msg = "❌ Error de Permiso."
            except Exception as e:
                denegacion_msg = f"❌ Error: {e}"

        await interaction.message.edit(content=f"❌ Ticket **DENEGADO** por {interaction.user.mention}. {denegacion_msg}", view=None)
        await interaction.response.send_message(f"Eliminando en 10 segundos...", ephemeral=True)
        await asyncio.sleep(10)
        await interaction.channel.delete()

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar", row=1)
    async def cerrar_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Ticket cerrado. Eliminando en 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()


# -----------------------------------------------------------------------
# --- 3. EVENTOS DEL BOT ------------------------------------------------
# -----------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f'🤖 Bot conectado como: {bot.user.name}')
    if not hasattr(bot, 'persistent_views_added'):
        bot.add_view(TicketView())
        bot.add_view(GestionTicketView(ticket_opener=None))
        setattr(bot, 'persistent_views_added', True)
        print('✅ Vistas persistentes cargadas.')
    print('-------------------------------------------')

@bot.event
async def on_member_update(before, after):
    ROL_PROHIBIDO_NORMALIZADO = "expulsado" 
    roles_before = set(r.name.strip().lower() for r in before.roles)
    roles_after = set(r.name.strip().lower() for r in after.roles)
    roles_added = roles_after.difference(roles_before)

    if ROL_PROHIBIDO_NORMALIZADO in roles_added:
        try:
            nombre_rol_real = [r.name for r in after.roles if r.name.strip().lower() == ROL_PROHIBIDO_NORMALIZADO][0]
            await after.kick(reason=f"Automático: Rol prohibido {nombre_rol_real}")
            print(f"➡️ {after.name} expulsado.")
        except Exception as e:
            print(f"❌ Error al expulsar: {e}")

# -----------------------------------------------------------------------
# --- 4. COMANDOS DEL BOT -----------------------------------------------
# -----------------------------------------------------------------------

@bot.command()
@commands.has_permissions(administrator=True) 
async def enviarticket(ctx):
    embed = discord.Embed(
        title="Sistema de Soporte y Verificación 🎫",
        description="Por favor, crea tu ticket para poder iniciar el proceso.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

@bot.command()
@commands.has_permissions(manage_channels=True)
async def cerrar(ctx):
    if ctx.channel.name.startswith('ticket-'):
        await ctx.channel.delete()

# -----------------------------------------------------------------------
# --- 5. EJECUTAR EL BOT -----------------------------------------------
# -----------------------------------------------------------------------

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN") 

if TOKEN:
    try:
        keep_alive() # Lanzamos el servidor Flask para Render
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Error: {e}")
