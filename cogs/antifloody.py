import discord
from discord.ext import commands
from discord import app_commands
import json, os, time
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "antiflood.json")

# ============================================================
# CONFIG
# ============================================================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ============================================================
# COG ANTI-FLOOD (VERSIÓN PROFESIONAL)
# ============================================================

class AntiFlood(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.user_messages = {}
        self.warned = {}
        self.last_flood = {}

    # --------------------------------------------------------
    # LOGS
    # --------------------------------------------------------

    async def send_log(self, guild, embed):
        cfg = self.ensure_guild(guild.id)
        log_channel_id = cfg.get("log_channel")

        if not log_channel_id:
            return

        canal = guild.get_channel(log_channel_id)
        if canal:
            try:
                await canal.send(embed=embed)
            except:
                pass

    # --------------------------------------------------------
    # CONFIG POR SERVIDOR
    # --------------------------------------------------------

    def ensure_guild(self, guild_id: int):
        gid = str(guild_id)

        if gid not in self.config:
            self.config[gid] = {
                "enabled": False,
                "nivel": "medio",
                "accion": "mute",
                "mute_time": 600,
                "log_channel": None,

                "settings": {
                    "interval": 4,
                    "max_messages": 5,
                    "delete_count": 2
                }
            }
            save_config(self.config)

        return self.config[gid]

    # --------------------------------------------------------
    # COMANDO /antiflood
    # --------------------------------------------------------

    @app_commands.command(
        name="antiflood",
        description="Configura el sistema Anti-Flood del servidor."
    )
    @app_commands.describe(
        estado="Activar o desactivar el sistema",
        nivel="Nivel de sensibilidad",
        accion="Acción al detectar flood",
        mute_time="Duración del mute en segundos",
        logs="Canal donde se enviarán los registros"
    )
    @app_commands.choices(
        estado=[
            app_commands.Choice(name="Activar", value="activar"),
            app_commands.Choice(name="Desactivar", value="desactivar")
        ],
        nivel=[
            app_commands.Choice(name="Bajo", value="bajo"),
            app_commands.Choice(name="Medio", value="medio"),
            app_commands.Choice(name="Alto", value="alto")
        ],
        accion=[
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban")
        ]
    )
    async def antiflood_cmd(
        self,
        interaction: discord.Interaction,
        estado: str = None,
        nivel: str = None,
        accion: str = None,
        mute_time: int = None,
        logs: discord.TextChannel = None
    ):
        guild = interaction.guild
        cfg = self.ensure_guild(guild.id)

        if estado:
            cfg["enabled"] = (estado == "activar")

        if nivel:
            cfg["nivel"] = nivel

            if nivel == "bajo":
                cfg["settings"]["interval"] = 3
                cfg["settings"]["max_messages"] = 7
                cfg["settings"]["delete_count"] = 1

            elif nivel == "medio":
                cfg["settings"]["interval"] = 4
                cfg["settings"]["max_messages"] = 5
                cfg["settings"]["delete_count"] = 2

            elif nivel == "alto":
                cfg["settings"]["interval"] = 5
                cfg["settings"]["max_messages"] = 3
                cfg["settings"]["delete_count"] = 3

        if accion:
            cfg["accion"] = accion

        if mute_time:
            cfg["mute_time"] = max(1, mute_time)

        if logs:
            cfg["log_channel"] = logs.id

        save_config(self.config)

        embed = discord.Embed(
            title="🔧 Configuración Anti-Flood actualizada",
            color=discord.Color.blue()
        )

        embed.add_field(name="Estado", value="Activado" if cfg["enabled"] else "Desactivado", inline=False)
        embed.add_field(name="Nivel", value=cfg["nivel"].capitalize(), inline=True)
        embed.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        embed.add_field(name="Mute", value=f"{cfg['mute_time']}s", inline=True)
        embed.add_field(
            name="Límite",
            value=f"{cfg['settings']['max_messages']} mensajes / {cfg['settings']['interval']}s",
            inline=False
        )
        embed.add_field(
            name="Logs",
            value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log
        log = discord.Embed(
            title="📘 Registro de configuración Anti-Flood",
            color=discord.Color.blue()
        )
        log.add_field(name="Servidor", value=f"{guild.name} (`{guild.id}`)", inline=False)
        log.add_field(name="Mod", value=f"{interaction.user} (`{interaction.user.id}`)", inline=False)
        log.add_field(name="Estado", value="Activado" if cfg["enabled"] else "Desactivado", inline=True)
        log.add_field(name="Nivel", value=cfg["nivel"].capitalize(), inline=True)
        log.add_field(name="Acción", value=cfg["accion"].capitalize(), inline=True)
        log.add_field(name="Mute", value=f"{cfg['mute_time']}s", inline=True)
        log.add_field(name="Logs", value=f"<#{cfg['log_channel']}>" if cfg["log_channel"] else "No configurado", inline=False)
        log.timestamp = discord.utils.utcnow()

        await self.send_log(guild, log)

    # --------------------------------------------------------
    # DETECCIÓN DE FLOOD
    # --------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild = message.guild
        user = message.author
        cfg = self.ensure_guild(guild.id)
        now = time.time()

        if not cfg["enabled"]:
            return

        key = (guild.id, user.id)

        if key not in self.user_messages:
            self.user_messages[key] = []

        self.user_messages[key].append((now, message))

        interval = cfg["settings"]["interval"]
        max_msgs = cfg["settings"]["max_messages"]
        delete_count = cfg["settings"]["delete_count"]

        # Limpiar mensajes viejos
        self.user_messages[key] = [
            (t, msg) for t, msg in self.user_messages[key]
            if now - t <= interval
        ]

        # Flood detectado
        if len(self.user_messages[key]) >= max_msgs:

            # Evitar duplicados
            if key in self.last_flood and now - self.last_flood[key] < interval:
                return
            self.last_flood[key] = now

            # Borrar mensajes
            to_delete = [msg for _, msg in self.user_messages[key][-delete_count:]]
            for msg in to_delete:
                try:
                    await msg.delete()
                except:
                    pass

            # Primer aviso
            last_warn = self.warned.get(key, 0)

            if now - last_warn > 10:
                self.warned[key] = now

                embed = discord.Embed(
                    title="⚠️ Aviso de Flood",
                    description=f"{user.mention}, estás enviando mensajes demasiado rápido.\nPor favor, reduce la velocidad.",
                    color=discord.Color.blue()
                )
                await message.channel.send(embed=embed)

                # Log
                log = discord.Embed(
                    title="⚠️ Aviso de Flood",
                    color=discord.Color.blue()
                )
                log.add_field(name="Usuario", value=f"{user} (`{user.id}`)", inline=False)
                log.add_field(name="Canal", value=f"{message.channel.mention}", inline=False)
                log.add_field(name="Detalle", value=f"{len(self.user_messages[key])} mensajes en {interval}s", inline=False)
                log.timestamp = discord.utils.utcnow()

                await self.send_log(guild, log)
                return

            # Si ya fue avisado → sanción
            await self.apply_action(message, cfg, key)

    # --------------------------------------------------------
    # APLICAR SANCIÓN
    # --------------------------------------------------------

    async def apply_action(self, message: discord.Message, cfg, key):
        user = message.author
        guild = message.guild
        action = cfg["accion"]

        sancionado = False

        try:
            if action == "ban":
                await guild.ban(user, reason="Flood")
            elif action == "kick":
                await guild.kick(user, reason="Flood")
            elif action == "mute":
                duration = cfg["mute_time"]
                await user.timeout(
                    discord.utils.utcnow() + timedelta(seconds=duration),
                    reason="Flood"
                )
            sancionado = True
        except:
            sancionado = False

        # Si NO se pudo sancionar
        if not sancionado:
            embed = discord.Embed(
                title="🚫 No se pudo aplicar la sanción",
                description=f"No tengo permisos suficientes para sancionar a {user.mention}.",
                color=discord.Color.blue()
            )
            await message.channel.send(embed=embed)

            # Log
            log = discord.Embed(
                title="🚫 Error al aplicar sanción",
                color=discord.Color.blue()
            )
            log.add_field(name="Usuario", value=f"{user} (`{user.id}`)", inline=False)
            log.add_field(name="Acción configurada", value=action, inline=False)
            log.add_field(name="Resultado", value="Fallo por falta de permisos", inline=False)
            log.timestamp = discord.utils.utcnow()

            await self.send_log(guild, log)
            return

        # Si SÍ se sancionó
        embed = discord.Embed(
            title="🔨 Sanción aplicada",
            description=f"Usuario: {user.mention}\nAcción: **{action}**\nMotivo: Flood",
            color=discord.Color.blue()
        )
        await message.channel.send(embed=embed)

        # Log
        log = discord.Embed(
            title="🔨 Sanción aplicada",
            color=discord.Color.blue()
        )
        log.add_field(name="Usuario", value=f"{user} (`{user.id}`)", inline=False)
        log.add_field(name="Acción", value=action, inline=False)
        if action == "mute":
            log.add_field(name="Duración", value=f"{cfg['mute_time']}s", inline=False)
        log.timestamp = discord.utils.utcnow()

        await self.send_log(guild, log)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiFlood(bot))
