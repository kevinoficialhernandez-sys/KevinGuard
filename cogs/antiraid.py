# antiraid.py
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import json
import os
from typing import Dict, Any, Optional, List

ANTIRAID_FILE = "antiraid_config.json"


# ============================================================
# JSON
# ============================================================

def load_antiraid_config() -> Dict[str, Any]:
    if not os.path.exists(ANTIRAID_FILE):
        return {}
    with open(ANTIRAID_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_antiraid_config(data: Dict[str, Any]):
    with open(ANTIRAID_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ============================================================
# MODELO DE CONFIGURACIÓN
# ============================================================

class AntiRaidGuildConfig:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id

        # Configuración
        self.enabled = True

        self.log_channel_id: Optional[int] = None

        self.anti_mass_join_enabled = True
        self.mass_join_threshold = 5
        self.mass_join_interval = 10

        self.anti_mass_channel_delete_enabled = True
        self.mass_channel_delete_threshold = 3
        self.mass_channel_delete_interval = 15

        # Estado interno
        self._recent_joins: List[datetime.datetime] = []
        self._recent_deletes: List[datetime.datetime] = []

    # Serializar
    def to_dict(self):
        return {
            "guild_id": self.guild_id,
            "enabled": self.enabled,
            "log_channel_id": self.log_channel_id,
            "anti_mass_join_enabled": self.anti_mass_join_enabled,
            "mass_join_threshold": self.mass_join_threshold,
            "mass_join_interval": self.mass_join_interval,
            "anti_mass_channel_delete_enabled": self.anti_mass_channel_delete_enabled,
            "mass_channel_delete_threshold": self.mass_channel_delete_threshold,
            "mass_channel_delete_interval": self.mass_channel_delete_interval,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        cfg = AntiRaidGuildConfig(data["guild_id"])
        cfg.enabled = data.get("enabled", True)
        cfg.log_channel_id = data.get("log_channel_id")
        cfg.anti_mass_join_enabled = data.get("anti_mass_join_enabled", True)
        cfg.mass_join_threshold = data.get("mass_join_threshold", 5)
        cfg.mass_join_interval = data.get("mass_join_interval", 10)
        cfg.anti_mass_channel_delete_enabled = data.get("anti_mass_channel_delete_enabled", True)
        cfg.mass_channel_delete_threshold = data.get("mass_channel_delete_threshold", 3)
        cfg.mass_channel_delete_interval = data.get("mass_channel_delete_interval", 15)
        return cfg

    # Detección de joins masivos
    def register_join(self) -> bool:
        now = datetime.datetime.utcnow()
        self._recent_joins.append(now)

        self._recent_joins = [
            t for t in self._recent_joins
            if (now - t).total_seconds() <= self.mass_join_interval
        ]

        return (
            self.anti_mass_join_enabled
            and len(self._recent_joins) >= self.mass_join_threshold
        )

    # Detección de borrado masivo
    def register_delete(self) -> bool:
        now = datetime.datetime.utcnow()
        self._recent_deletes.append(now)

        self._recent_deletes = [
            t for t in self._recent_deletes
            if (now - t).total_seconds() <= self.mass_channel_delete_interval
        ]

        return (
            self.anti_mass_channel_delete_enabled
            and len(self._recent_deletes) >= self.mass_channel_delete_threshold
        )


# ============================================================
# SELECT MENU
# ============================================================

class AntiRaidSelect(discord.ui.Select):
    def __init__(self, cog, config):
        self.cog = cog
        self.config = config

        options = [
            discord.SelectOption(label="Canal de logs", value="logs", emoji="📜"),
            discord.SelectOption(label="Anti-join masivo", value="joins", emoji="👥"),
            discord.SelectOption(label="Anti-borrado masivo", value="delete", emoji="🗑️"),
            discord.SelectOption(label="Activar/Desactivar Anti-Raid", value="toggle", emoji="⚙️"),
        ]

        super().__init__(placeholder="Selecciona una opción…", options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]

        if value == "logs":
            await self.configure_logs(interaction)
        elif value == "joins":
            await self.configure_joins(interaction)
        elif value == "delete":
            await self.configure_delete(interaction)
        elif value == "toggle":
            self.config.enabled = not self.config.enabled
            self.cog.save_all()
            await interaction.response.send_message(
                f"✅ Anti-Raid ahora está **{'activado' if self.config.enabled else 'desactivado'}**",
                ephemeral=True
            )

    # Configurar canal de logs
    async def configure_logs(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "📜 Menciona el canal de logs o escribe su ID.",
            ephemeral=True
        )

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            msg = await interaction.client.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            return await interaction.followup.send("⏰ Tiempo agotado.", ephemeral=True)

        channel = None

        if msg.channel_mentions:
            channel = msg.channel_mentions[0]
        else:
            try:
                channel = interaction.guild.get_channel(int(msg.content))
            except:
                pass

        if not channel:
            return await interaction.followup.send("❌ Canal inválido.", ephemeral=True)

        self.config.log_channel_id = channel.id
        self.cog.save_all()

        await interaction.followup.send(f"✅ Canal de logs establecido en {channel.mention}", ephemeral=True)

    # Configurar joins masivos
    async def configure_joins(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "👥 Envía: `on`, `off` o `<joins> <segundos>`\nEjemplo: `5 10`",
            ephemeral=True
        )

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            msg = await interaction.client.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            return await interaction.followup.send("⏰ Tiempo agotado.", ephemeral=True)

        content = msg.content.lower().strip()

        if content in ("on", "off"):
            self.config.anti_mass_join_enabled = content == "on"
        else:
            try:
                j, s = content.split()
                self.config.mass_join_threshold = int(j)
                self.config.mass_join_interval = int(s)
            except:
                return await interaction.followup.send("❌ Formato inválido.", ephemeral=True)

        self.cog.save_all()
        await interaction.followup.send("✅ Configuración actualizada.", ephemeral=True)

    # Configurar borrado masivo
    async def configure_delete(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "🗑️ Envía: `on`, `off` o `<borrados> <segundos>`",
            ephemeral=True
        )

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id

        try:
            msg = await interaction.client.wait_for("message", timeout=30, check=check)
        except asyncio.TimeoutError:
            return await interaction.followup.send("⏰ Tiempo agotado.", ephemeral=True)

        content = msg.content.lower().strip()

        if content in ("on", "off"):
            self.config.anti_mass_channel_delete_enabled = content == "on"
        else:
            try:
                d, s = content.split()
                self.config.mass_channel_delete_threshold = int(d)
                self.config.mass_channel_delete_interval = int(s)
            except:
                return await interaction.followup.send("❌ Formato inválido.", ephemeral=True)

        self.cog.save_all()
        await interaction.followup.send("✅ Configuración actualizada.", ephemeral=True)


class AntiRaidView(discord.ui.View):
    def __init__(self, cog, config):
        super().__init__(timeout=120)
        self.add_item(AntiRaidSelect(cog, config))


# ============================================================
# COG PRINCIPAL
# ============================================================

class AntiRaidCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guilds: Dict[int, AntiRaidGuildConfig] = {}
        self.load_all()

    # JSON
    def load_all(self):
        raw = load_antiraid_config()
        for gid, data in raw.items():
            self.guilds[int(gid)] = AntiRaidGuildConfig.from_dict(data)

    def save_all(self):
        raw = {gid: cfg.to_dict() for gid, cfg in self.guilds.items()}
        save_antiraid_config(raw)

    def get_config(self, guild: discord.Guild):
        if guild.id not in self.guilds:
            self.guilds[guild.id] = AntiRaidGuildConfig(guild.id)
            self.save_all()
        return self.guilds[guild.id]

    # Logs
    async def log(self, guild: discord.Guild, title: str, desc: str):
        cfg = self.get_config(guild)
        if not cfg.log_channel_id:
            return

        channel = guild.get_channel(cfg.log_channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        await channel.send(embed=embed)

    # Panel
    @app_commands.command(name="antiraid", description="Panel de configuración Anti-Raid")
    @app_commands.checks.has_permissions(administrator=True)
    async def antiraid(self, interaction: discord.Interaction):
        cfg = self.get_config(interaction.guild)

        embed = discord.Embed(
            title="🛡️ Panel Anti-Raid",
            description="Configura el sistema Anti-Raid usando el menú.",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=AntiRaidView(self, cfg),
            ephemeral=True
        )

    # Eventos
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        cfg = self.get_config(member.guild)
        if not cfg.enabled:
            return

        # Comprobar blacklist global
        blacklist = self.bot.get_cog("GlobalBlacklistCog")
        if blacklist and blacklist.is_blacklisted(member.id):
            try:
                await member.guild.ban(member, reason="Blacklist global")
            except:
                pass
            return

        # Detección de raid
        if cfg.register_join():
            await self.log(
                member.guild,
                "🚨 Raid detectado",
                f"Joins masivos detectados. Último: {member.mention}"
            )

            # Añadir a blacklist global
            if blacklist:
                await blacklist.ban_globally(
                    user_id=member.id,
                    reason="Raid (joins masivos)",
                    proofs=[]
                )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        cfg = self.get_config(channel.guild)
        if not cfg.enabled:
            return

        if cfg.register_delete():
            await self.log(
                channel.guild,
                "🚨 Raid detectado",
                f"Borrado masivo de canales. Último: `{channel.name}`"
            )


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(AntiRaidCog(bot))
