# globalblacklist.py
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import datetime
import asyncio
from typing import Dict, Any, List, Optional

BLACKLIST_FILE = "global_blacklist.json"

# Servidor donde NO se aplicará el ban global
EXCLUDED_GUILDS = [
    1485789239647146115  # Servidor de soporte
]


# ============================================================
# JSON
# ============================================================

def load_blacklist() -> Dict[str, Any]:
    if not os.path.exists(BLACKLIST_FILE):
        return {}
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_blacklist(data: Dict[str, Any]):
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ============================================================
# MODELO DE ENTRADA
# ============================================================

class BlacklistEntry:
    def __init__(
        self,
        user_id: int,
        username: str,
        reason: str,
        proofs: Optional[List[str]] = None,
        created_at: Optional[str] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.reason = reason
        self.proofs = proofs or []
        self.created_at = created_at or datetime.datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "reason": self.reason,
            "proofs": self.proofs,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BlacklistEntry":
        return BlacklistEntry(
            user_id=data["user_id"],
            username=data.get("username", "Desconocido"),
            reason=data.get("reason", "Sin razón"),
            proofs=data.get("proofs", []),
            created_at=data.get("created_at"),
        )


# ============================================================
# MODALS
# ============================================================

class BlacklistModal(discord.ui.Modal, title="Añadir a blacklist global"):
    def __init__(self, cog: "GlobalBlacklistCog"):
        super().__init__(timeout=300)
        self.cog = cog

        self.user_field = discord.ui.TextInput(
            label="Usuario o ID",
            placeholder="Ej: 123456789012345678 o @usuario",
            required=True,
            max_length=50,
        )
        self.reason_field = discord.ui.TextInput(
            label="Razón",
            style=discord.TextStyle.paragraph,
            placeholder="Explica por qué entra en la blacklist",
            required=True,
            max_length=400,
        )

        self.add_item(self.user_field)
        self.add_item(self.reason_field)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.handle_blacklist_modal_submit(interaction, self)


class UnblacklistModal(discord.ui.Modal, title="Quitar de blacklist global"):
    def __init__(self, cog: "GlobalBlacklistCog"):
        super().__init__(timeout=300)
        self.cog = cog

        self.user_field = discord.ui.TextInput(
            label="Usuario o ID",
            placeholder="Ej: 123456789012345678 o @usuario",
            required=True,
            max_length=50,
        )

        self.add_item(self.user_field)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.handle_unblacklist_modal_submit(interaction, self)


# ============================================================
# COG PRINCIPAL
# ============================================================

class GlobalBlacklistCog(commands.Cog):
    """
    Blacklist global:
    - /blacklist → modal
    - /blacklistinspect
    - /blacklistlist
    - /unblacklist
    - Ban global (excepto en servidores excluidos)
    - Auto-ban al entrar (excepto en servidores excluidos)
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.blacklist: Dict[str, Any] = load_blacklist()

    # --------------------------------------------------------
    # UTILIDADES
    # --------------------------------------------------------
    def is_blacklisted(self, user_id: int) -> bool:
        return str(user_id) in self.blacklist

    def get_entry(self, user_id: int) -> Optional[BlacklistEntry]:
        data = self.blacklist.get(str(user_id))
        if not data:
            return None
        return BlacklistEntry.from_dict(data)

    def add_entry(self, entry: BlacklistEntry):
        self.blacklist[str(entry.user_id)] = entry.to_dict()
        save_blacklist(self.blacklist)

    def remove_entry(self, user_id: int) -> bool:
        key = str(user_id)
        if key in self.blacklist:
            del self.blacklist[key]
            save_blacklist(self.blacklist)
            return True
        return False

    # --------------------------------------------------------
    # BAN GLOBAL
    # --------------------------------------------------------
    async def ban_globally(
        self,
        user_id: int,
        reason: str,
        proofs: Optional[List[str]] = None,
        source_guild: Optional[discord.Guild] = None,
    ):
        user: Optional[discord.User] = None
        try:
            user = await self.bot.fetch_user(user_id)
        except Exception:
            pass

        username = str(user) if user else f"ID {user_id}"

        entry = BlacklistEntry(
            user_id=user_id,
            username=username,
            reason=reason,
            proofs=proofs or [],
        )
        self.add_entry(entry)

        # Ban en todos los servidores excepto los excluidos
        for guild in self.bot.guilds:

            if guild.id in EXCLUDED_GUILDS:
                continue

            try:
                await guild.ban(
                    discord.Object(id=user_id),
                    reason=f"[GLOBAL BLACKLIST] {reason}",
                    delete_message_days=0,
                )
            except Exception:
                pass

        # DM al usuario
        if user:
            try:
                embed = discord.Embed(
                    title="🚫 Has sido añadido a una blacklist global",
                    description=(
                        "Has sido incluido en la **blacklist global** del bot.\n\n"
                        f"**Razón:** {reason}\n"
                        "Si crees que esto es un error, contacta con el staff."
                    ),
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.utcnow(),
                )

                if proofs:
                    embed.add_field(
                        name="Pruebas",
                        value="\n".join(proofs),
                        inline=False,
                    )

                await user.send(embed=embed)
            except Exception:
                pass

    # --------------------------------------------------------
    # HANDLER DEL MODAL
    # --------------------------------------------------------
    async def handle_blacklist_modal_submit(
        self,
        interaction: discord.Interaction,
        modal: BlacklistModal,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Necesitas permisos de administrador.",
                ephemeral=True,
            )
            return

        raw_user = modal.user_field.value.strip()
        reason = modal.reason_field.value.strip()

        target_user_id = None
        target_user = None

        # Resolver usuario
        try:
            target_user_id = int(raw_user)
            target_user = await self.bot.fetch_user(target_user_id)
        except Exception:
            pass

        if target_user is None and interaction.guild:
            member = discord.utils.find(
                lambda m: str(m) == raw_user or m.name == raw_user,
                interaction.guild.members,
            )
            if member:
                target_user = member
                target_user_id = member.id

        if target_user_id is None:
            await interaction.response.send_message(
                "❌ No he podido resolver ese usuario.",
                ephemeral=True,
            )
            return

        # Pedir pruebas
        await interaction.response.send_message(
            "📸 **Ahora envía las imágenes de prueba en los próximos 30 segundos.**\n"
            "Si no envías nada, se añadirá sin pruebas.",
            ephemeral=True,
        )

        proofs: List[str] = []

        def check(msg: discord.Message):
            return (
                msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel.id
                and msg.attachments
            )

        try:
            msg = await self.bot.wait_for("message", timeout=30.0, check=check)
            for att in msg.attachments:
                proofs.append(att.url)
        except asyncio.TimeoutError:
            pass

        # Ban global
        await self.ban_globally(
            user_id=target_user_id,
            reason=reason,
            proofs=proofs,
            source_guild=interaction.guild,
        )

        await interaction.followup.send(
            f"✅ Usuario `{target_user_id}` añadido a la blacklist global.\n"
            f"📨 Pruebas guardadas: **{len(proofs)}**",
            ephemeral=True,
        )

    # --------------------------------------------------------
    # HANDLER UNBLACKLIST
    # --------------------------------------------------------
    async def handle_unblacklist_modal_submit(
        self,
        interaction: discord.Interaction,
        modal: UnblacklistModal,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Necesitas permisos de administrador.",
                ephemeral=True,
            )
            return

        raw_user = modal.user_field.value.strip()

        try:
            target_user_id = int(raw_user)
        except ValueError:
            await interaction.response.send_message(
                "❌ Usa una ID válida.",
                ephemeral=True,
            )
            return

        removed = self.remove_entry(target_user_id)
        if removed:
            await interaction.response.send_message(
                f"✅ Usuario `{target_user_id}` eliminado de la blacklist.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Ese usuario no estaba en la blacklist.",
                ephemeral=True,
            )

    # --------------------------------------------------------
    # COMANDOS
    # --------------------------------------------------------
    @app_commands.command(name="blacklist", description="Añadir a la blacklist global.")
    async def blacklist_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BlacklistModal(self))

    @app_commands.command(name="blacklistinspect", description="Ver detalles de un usuario.")
    async def blacklist_inspect(self, interaction: discord.Interaction, user: discord.User):
        entry = self.get_entry(user.id)
        if not entry:
            await interaction.response.send_message(
                "❌ Ese usuario no está en la blacklist.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"Blacklist global - {entry.username}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.add_field(name="ID", value=str(entry.user_id), inline=False)
        embed.add_field(name="Razón", value=entry.reason, inline=False)
        embed.add_field(name="Fecha", value=entry.created_at, inline=False)

        if entry.proofs:
            embed.add_field(
                name="Pruebas",
                value="\n".join(entry.proofs),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="blacklistlist", description="Lista completa de la blacklist.")
    async def blacklist_list(self, interaction: discord.Interaction):
        if not self.blacklist:
            await interaction.response.send_message(
                "✅ La blacklist está vacía.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Lista de blacklist global",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.utcnow(),
        )

        desc = ""
        for uid, data in self.blacklist.items():
            entry = BlacklistEntry.from_dict(data)
            desc += (
                f"**{entry.username}** (`{entry.user_id}`)\n"
                f"Razón: {entry.reason}\n"
                f"Fecha: {entry.created_at}\n\n"
            )

        embed.description = desc[:4000]
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unblacklist", description="Quitar de la blacklist global.")
    async def unblacklist_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_modal(UnblacklistModal(self))

    # --------------------------------------------------------
    # AUTO-BAN AL ENTRAR
    # --------------------------------------------------------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        # Si el servidor está excluido, no hacer nada
        if member.guild.id in EXCLUDED_GUILDS:
            return

        if self.is_blacklisted(member.id):
            try:
                await member.guild.ban(
                    member,
                    reason="[GLOBAL BLACKLIST] Intento de entrar estando en blacklist.",
                    delete_message_days=0,
                )
            except Exception:
                pass


# ============================================================
# SETUP
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(GlobalBlacklistCog(bot))
