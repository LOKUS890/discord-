import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput 
import asyncio 

# --- AÑADIDOS PARA EL HOSTING 24/7 ---
from dotenv import load_dotenv
import os
# ------------------------------------

# --- 1. CONFIGURACIÓN DEL BOT Y INTENTS ---
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# -----------------------------------------------------------------------
# --- 2. CLASES DE MODALS Y VISTAS (BOTONES) ----------------------------
# -----------------------------------------------------------------------

# CLASE 2.1: MODAL (FORMULARIO DE PREGUNTAS) - Contiene el formulario
class TicketModal(Modal, title="Abrir Nuevo Ticket de Soporte"):
    
    # ✅ CORRECCIÓN: Label acortado a 45 caracteres o menos
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
        
        # Definir los roles de gestión para permisos y menciones
        rol_admin = discord.utils.get(guild.roles, name="Admin")
        rol_bot = discord.utils.get(guild.roles, name="bot")
        
        channel_name = f"ticket-{self.titulo.value.lower().replace(' ', '-')[:20]}-{user.discriminator}"
        
        # --- DEFINICIÓN DE PERMISOS ---
        overwrites = {
            # Ocultar para @everyone
            guild.default_role: discord.PermissionOverwrite(view_channel=False), 
            
            # Permisos del usuario que abre el ticket
            user: discord.PermissionOverwrite(
                view_channel=True, 
                send_messages=True,
                manage_channels=False, 
                manage_messages=False,
                add_reactions=False
            ),
            
            # Permiso del propio bot
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True) 
        }

        # Agregar permisos a los roles de gestión (Staff)
        if rol_admin:
            overwrites[rol_admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        
        if rol_bot:
            overwrites[rol_bot] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)

        # 1. Crear el canal
        ticket_channel = await guild.create_text_channel(
            channel_name, 
            overwrites=overwrites, 
            category=None,
            topic=f"Ticket de {user.name}: {self.titulo.value}"
        )

        # 2. Crear Embed con las respuestas del usuario
        embed_gestion = discord.Embed(
            title=f"Ticket Abierto: {self.titulo.value}",
            description=f"**Usuario:** {user.mention}\n**Red Social:** {self.titulo.value}\n**Invitado por:** {self.descripcion.value}", 
            color=discord.Color.yellow()
        )
        embed_gestion.set_footer(text=f"ID de Usuario: {user.id}")

        # 3. Enviar mensaje con las respuestas y los botones de gestión
        
        # ✅ CORRECCIÓN DEL TypeError: Usar un string para acumular las menciones
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
        
        # 4. Notificación al usuario
        await interaction.response.send_message(f"¡Tu ticket ha sido creado en {ticket_channel.mention}!", ephemeral=True)


# CLASE 2.2: BOTÓN PRINCIPAL - Abre el Modal
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="persistent_view:ticket_button")
    async def ticket_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal())


# CLASE 2.3: BOTONES DE GESTIÓN (APROBAR/DENEGAR + CERRAR)
class GestionTicketView(View):
    def __init__(self, ticket_opener):
        super().__init__(timeout=None)
        self.ticket_opener = ticket_opener
        
    # CRÍTICO: Comprueba si el usuario tiene permiso de STAFF antes de usar APROBAR/DENEGAR
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Requerimos el permiso de Gestionar Canales (manage_channels) para Staff
        is_staff = interaction.user.guild_permissions.manage_channels
        
        # Permitir que el botón de CERRAR siempre funcione (custom_id="ticket_cerrar")
        if interaction.data.get('custom_id') == 'ticket_cerrar':
            return True

        # Si no es staff y no es el botón de cerrar, bloquea la interacción
        if not is_staff:
            await interaction.response.send_message("⛔ Solo el staff de gestión puede usar los botones de Aprobar/Denegar.", ephemeral=True)
            return False
        
        return True # Permitir la interacción si es staff
        
    @discord.ui.button(label="✅ Aprobar", style=discord.ButtonStyle.green, custom_id="ticket_aprobado")
    async def aprobar_button(self, interaction: discord.Interaction, button: Button):
        
        # LÓGICA DE ROL: Asigna "Verificado"
        rol_verificado = discord.utils.get(interaction.guild.roles, name="Verificado") 
        aprobacion_msg = ""
        
        if rol_verificado:
            try:
                await self.ticket_opener.add_roles(rol_verificado)
                aprobacion_msg = f"✅ Rol **{rol_verificado.name}** otorgado a {self.ticket_opener.mention}."
            except discord.Forbidden:
                aprobacion_msg = "❌ Error de Permiso: El bot no pudo otorgar el rol (verifica la jerarquía)."
            except Exception as e:
                aprobacion_msg = f"❌ Error al otorgar rol: {e}"
        else:
            aprobacion_msg = "⚠️ Advertencia: Rol 'Verificado' no encontrado en el servidor."

        await interaction.message.edit(
            content=f"✅ Ticket **APROBADO** por {interaction.user.mention}. {aprobacion_msg}",
            view=None
        )
        
        await interaction.response.send_message(f"Ticket aprobado. Cerrando canal en 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket aprobado y cerrado automáticamente por {interaction.user.name}")
        
    @discord.ui.button(label="❌ Denegar", style=discord.ButtonStyle.red, custom_id="ticket_denegado")
    async def denegar_button(self, interaction: discord.Interaction, button: Button):
        
        # LÓGICA DE ROL: Asigna "expulsado"
        rol_expulsado = discord.utils.get(interaction.guild.roles, name="expulsado")
        denegacion_msg = ""
        
        if rol_expulsado:
            try:
                await self.ticket_opener.add_roles(rol_expulsado)
                denegacion_msg = f"⛔ Rol **{rol_expulsado.name}** otorgado a {self.ticket_opener.mention} (Expulsión inminente)."
            except discord.Forbidden:
                denegacion_msg = "❌ Error de Permiso: El bot no pudo otorgar el rol (jerarquía)."
            except Exception as e:
                denegacion_msg = f"❌ Error al otorgar rol: {e}"
        else:
            denegacion_msg = "⚠️ Advertencia: Rol 'expulsado' no encontrado en el servidor."

        await interaction.message.edit(
            content=f"❌ Ticket **DENEGADO** por {interaction.user.mention}. {denegacion_msg}",
            view=None
        )

        await interaction.response.send_message(f"Ticket denegado. Eliminando canal en 10 segundos...", ephemeral=True)
        await asyncio.sleep(10)
        await interaction.channel.delete(reason=f"Ticket denegado automáticamente por {interaction.user.name}")

    # Botón de Cierre para el usuario
    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.secondary, custom_id="ticket_cerrar", row=1)
    async def cerrar_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Ticket cerrado por el usuario. Eliminando canal en 5 segundos...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket cerrado por el usuario {interaction.user.name}")


# -----------------------------------------------------------------------
# --- 3. EVENTOS DEL BOT ------------------------------------------------
# -----------------------------------------------------------------------

@bot.event
async def on_ready():
    """Se ejecuta cuando el bot se conecta a Discord."""
    print(f'🤖 Bot conectado como: {bot.user.name}')
    
    if not hasattr(bot, 'persistent_views_added'):
        # Cargar vistas persistentes para que el botón de ticket funcione después de reiniciar el bot
        bot.add_view(TicketView())
        bot.add_view(GestionTicketView(ticket_opener=None)) # Necesario para que discord.py cargue los IDs
        setattr(bot, 'persistent_views_added', True)
        print('✅ Vistas persistentes de tickets cargadas.')
    
    print('-------------------------------------------')

@bot.event
async def on_member_update(before, after):
    """Expulsión automática si se añade el rol prohibido 'expulsado'."""
    
    ROL_PROHIBIDO_NORMALIZADO = "expulsado" 

    roles_before = set(r.name.strip().lower() for r in before.roles)
    roles_after = set(r.name.strip().lower() for r in after.roles)

    roles_added = roles_after.difference(roles_before)

    if ROL_PROHIBIDO_NORMALIZADO in roles_added:
        
        try:
            # Obtener el nombre de rol original
            nombre_rol_real = [r.name for r in after.roles if r.name.strip().lower() == ROL_PROHIBIDO_NORMALIZADO][0]
            reason = f"Automático: Recibió el rol prohibido: {nombre_rol_real}."
            
            await after.kick(reason=reason)
            print(f"➡️ Miembro {after.name} EXPULSADO CON ÉXITO por el rol '{nombre_rol_real}'.")
        
        except discord.Forbidden:
            print(f"❌ FALLO AL EXPULSAR: Permiso denegado (Jerarquía de rol).")
        except Exception as e:
            print(f"❌ FALLO AL EXPULSAR: Error desconocido: {e}")

# -----------------------------------------------------------------------
# --- 4. COMANDOS DEL BOT -----------------------------------------------
# -----------------------------------------------------------------------

@bot.command()
@commands.has_permissions(administrator=True) 
async def enviarticket(ctx):
    """Envía el mensaje fijo con el botón para crear tickets (Solo Administrador)."""
    
    embed = discord.Embed(
        title="Sistema de Soporte y Verificación 🎫",
        description="Por favor, crea tu ticket para poder iniciar el proceso de verificación o soporte.",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed, view=TicketView())
    await ctx.send("✅ El panel de tickets ha sido enviado.", delete_after=5)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def cerrar(ctx):
    """Cierra el canal de ticket actual (Respaldo si falla el botón)."""
    
    if ctx.channel.name.startswith('ticket-'):
        await ctx.send("Cerrando ticket en 5 segundos...")
        await ctx.channel.delete(reason=f"Ticket cerrado por {ctx.author.name}")
    else:
        await ctx.send("Este comando solo puede usarse en un canal de ticket.", delete_after=5)

# -----------------------------------------------------------------------
# --- 5. EJECUTAR EL BOT (TOKEN MODIFICADO) -----------------------------
# -----------------------------------------------------------------------

# Cargar variables desde el archivo .env (útil para pruebas locales)
load_dotenv()

# Obtener el token de la variable de entorno del sistema (DISCORD_TOKEN)
TOKEN = os.getenv("DISCORD_TOKEN") 

if TOKEN is None:
    print("\n\n❌ ERROR CRÍTICO: No se encontró la variable DISCORD_TOKEN.")
    print("Para 24/7, debes establecerla en el panel del hosting (Ej: Railway/Render).")
    print("Asegúrate de que la clave sea DISCORD_TOKEN.\n\n")
else:
    try:
        print("✅ Token cargado con éxito. Iniciando bot...")
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ ERROR al iniciar el bot: {e}")