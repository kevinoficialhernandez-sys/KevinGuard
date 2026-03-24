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
STAFF_FILE = "blacklist_staff.json"


EXCLUDED_GUILDS = [
    1485789239647146115  # Servidor de soporte
]


# ============================================================
# JSON
# ============================================================

def load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_json(path: str, data: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
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
# PERMISOS (STAFF)
# ============================================================

def is_staff(user_id: int) -> bool:
    data = load_json(STAFF_FILE)
    allowed = data.get("allowed_users", [])
    return user_id in allowed


def add_staff(user_id: int):
    data = load_json(STAFF_FILE)
    allowed = data.get("allowed_users", [])
    if user_id not in allowed:
        allowed.append(user_id)
    data["allowed_users"] = allowed
    save_json(STAFF_FILE, data)


def remove_staff(user_id: int):
    data = load_json(STAFF_FILE)
    allowed = data.get("allowed_users", [])
    if user_id in allowed:
        allowed.remove(user_id)
    data["allowed_users"] = allowed
    save_json(STAFF_FILE, data)


# ============================================================
# MODALS
# ============================================================

class AddBlacklistModal(discord.ui.Modal, title="Añadir a blacklist global"):
    def __init__(self, cog, target_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.target_id = target_id

        self.reason_field = discord.ui.TextInput(
            label="Razón",
            style=discord.TextStyle.paragraph,
            placeholder="Explica por qué entra en la blacklist",
            required=True,
            max_length=400,
        )

        self.add_item(self.reason_field)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.finish_add_blacklist(interaction, self.target_id, self.reason_field.value)


# ============================================================
# COG PRINCIPAL
# ============================================================

class GlobalBlacklistCog(commands.Cog):
    """
    Blacklist global con:
    - /blacklist perms
    - /blacklist add
    - /blacklist remove
    - /blacklist inspect
    - /blacklist list
    """

    def __init__(self, bot):
        self.bot = bot
        self.blacklist = load_json(BLACKLIST_FILE)

    # ============================================================
    # UTILIDADES
    # ============================================================

    def save_blacklist(self):
        save_json(BLACKLIST_FILE, self.blacklist)

    def is_blacklisted(self, user_id: int) -> bool:
        return str(user_id) in self.blacklist

    def add_entry(self, entry: BlacklistEntry):
        self.blacklist[str(entry.user_id)] = entry.to_dict()
        self.save_blacklist()

    def remove_entry(self, user_id: int):
        if str(user_id) in self.blacklist:
            del self.blacklist[str(user_id)]
            self.save_blacklist()
            return True
        return False

    # ============================================================
    # BAN GLOBAL
    # ============================================================

    async def ban_globally(self, user_id: int, reason: str, proofs: List[str]):
        user = None
        try:
            user = await self.bot.fetch_user(user_id)
        except:
            pass

        entry = BlacklistEntry(
            user_id=user_id,
            username=str(user) if user else f"ID {user_id}",
            reason=reason,
            proofs=proofs
        )
        self.add_entry(entry)

        # Ban en todos los servidores excepto soporte
        for guild in self.bot.guilds:
            if guild.id in EXCLUDED_GUILDS:
                continue
            try:
                await guild.ban(
                    discord.Object(id=user_id),
                    reason=f"[GLOBAL BLACKLIST] {reason}",
                    delete_message_days=0
                )
            except:
                pass

        # DM
if user:
    try:
        embed = discord.Embed(
            title="🚫 Has sido añadido a una Blacklist Global",
            color=discord.Color.red()
        )

        embed.add_field(
            name="📌 ¿Qué significa esto?",
            value=(
                "Has sido registrado en un sistema de seguridad global utilizado por múltiples servidores. "
                "Este sistema se emplea para identificar y marcar usuarios relacionados con actividades "
                "potencialmente dañinas, como raids, abusos de permisos o comportamientos sospechosos."
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Razón del registro",
            value=f"{reason}",
            inline=False
        )

        if proofs:
            embed.add_field(
                name="📁 Pruebas adjuntas",
                value="\n".join(proofs),
                inline=False
            )

        embed.add_field(
            name="📅 Fecha del registro",
            value=f"<t:{int(time.time())}:F>",
            inline=False
        )

        embed.add_field(
            name="⚠️ Consecuencias",
            value=(
                "Este sistema usa un auto ban automático para prevenir otros raideos y mantener comunidades seguras "
                "**Seras automáticamentebaneado de todos los servidores en los que el bot esté**"
                "Esto no significa que estes baneado de por vida, tienes una opcion para apelar \n\n"
                "Dependiendo de tus actos sera apelable o no."
            ),
            inline=False
        )

        embed.add_field(
            name="🔍 ¿Qué puedes hacer?",
            value=(
                "Si consideras que este registro es un error o deseas apelar tu caso, puedes ponerte"
                "en contacto con el equipo de soporte. Allí podrás explicar tu situación y solicitar"
                "una revisión manual de tu caso.\n\n"
                "**Servidor de soporte:**\n"
                "[Haz clic aquí para unirte](https://discord.gg/nSwqZyphhN)"
            ),
            inline=False
        )

        embed.set_footer(text="Sistema de Seguridad Global")

        await user.send(embed=embed)

    except:
        pass
    # ============================================================
    # /blacklist perms
    # ============================================================

    @app_commands.command(
        name="blacklist_perms",
        description="Gestionar permisos de quién puede usar la blacklist global."
    )
    @app_commands.describe(
        accion="Acción a realizar",
        usuario="ID o nombre del usuario"
    )
    @app_commands.choices(
        accion=[
            app_commands.Choice(name="Añadir", value="add"),
            app_commands.Choice(name="Eliminar", value="remove")
        ]
    )
    async def blacklist_perms(self, interaction: discord.Interaction, accion: app_commands.Choice[str], usuario: str):

        # Solo el owner del bot puede gestionar permisos
        if interaction.user.id != interaction.client.owner_id:
            return await interaction.response.send_message(
                "❌ Solo el **owner del bot** puede gestionar permisos.",
                ephemeral=True
            )

        # Resolver usuario
        target_id = None

        try:
            target_id = int(usuario)
        except:
            if interaction.guild:
                member = discord.utils.find(
                    lambda m: m.name == usuario or str(m) == usuario,
                    interaction.guild.members
                )
                if member:
                    target_id = member.id

        if target_id is None:
            return await interaction.response.send_message(
                "❌ No pude resolver ese usuario.",
                ephemeral=True
            )

        # Acción
        if accion.value == "add":
            add_staff(target_id)
            return await interaction.response.send_message(
                f"✅ Usuario `{target_id}` añadido a la whitelist de staff.",
                ephemeral=True
            )

        if accion.value == "remove":
            remove_staff(target_id)
            return await interaction.response.send_message(
                f"🗑️ Usuario `{target_id}` eliminado de la whitelist de staff.",
                ephemeral=True
            )

    # ============================================================
    # /blacklist add
    # ============================================================

    @app_commands.command(name="blacklist_add", description="Añadir usuario a la blacklist global.")
    async def blacklist_add(self, interaction: discord.Interaction, usuario: str):

        if not is_staff(interaction.user.id):
            return await interaction.response.send_message(
                "❌ No tienes permisos para usar este comando.",
                ephemeral=True
            )

        # Resolver usuario
        target_id = None
        try:
            target_id = int(usuario)
        except:
            if interaction.guild:
                member = discord.utils.find(
                    lambda m: m.name == usuario or str(m) == usuario,
                    interaction.guild.members
                )
                if member:
                    target_id = member.id

        if target_id is None:
            return await interaction.response.send_message("❌ Usuario no encontrado.", ephemeral=True)

        await interaction.response.send_modal(AddBlacklistModal(self, target_id))

    # ============================================================
    # FINALIZAR AÑADIR (modal + pruebas)
    # ============================================================

    async def finish_add_blacklist(self, interaction: discord.Interaction, target_id: int, reason: str):

        await interaction.response.send_message(
            "📸 Envía las imágenes de prueba en los próximos **30 segundos**.",
            ephemeral=True
        )

        proofs = []

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel.id == interaction.channel.id and msg.attachments

        try:
            msg = await self.bot.wait_for("message", timeout=30, check=check)
            for att in msg.attachments:
                proofs.append(att.url)
        except asyncio.TimeoutError:
            pass

        await self.ban_globally(target_id, reason, proofs)

        await interaction.followup.send(
            f"✅ Usuario `{target_id}` añadido a la blacklist global.\n"
            f"📨 Pruebas guardadas: **{len(proofs)}**",
            ephemeral=True
        )

    # ============================================================
    # /blacklist remove
    # ============================================================

    @app_commands.command(name="blacklist_remove", description="Eliminar usuario de la blacklist global.")
    async def blacklist_remove(self, interaction: discord.Interaction, usuario: str):

        if not is_staff(interaction.user.id):
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        try:
            target_id = int(usuario)
        except:
            return await interaction.response.send_message("❌ Usa una ID válida.", ephemeral=True)

        if self.remove_entry(target_id):
            return await interaction.response.send_message(
                f"🗑️ Usuario `{target_id}` eliminado de la blacklist.",
                ephemeral=True
            )

        return await interaction.response.send_message("❌ Ese usuario no estaba en la blacklist.", ephemeral=True)

    # ============================================================
    # /blacklist inspect
    # ============================================================

    @app_commands.command(name="blacklist_inspect", description="Ver información de un usuario en la blacklist.")
    async def blacklist_inspect(self, interaction: discord.Interaction, usuario: str):

        if not is_staff(interaction.user.id):
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        try:
            target_id = int(usuario)
        except:
            return await interaction.response.send_message("❌ Usa una ID válida.", ephemeral=True)

        if not self.is_blacklisted(target_id):
            return await interaction.response.send_message("❌ Ese usuario no está en la blacklist.", ephemeral=True)

        entry = BlacklistEntry.from_dict(self.blacklist[str(target_id)])

        embed = discord.Embed(
            title=f"Blacklist - {entry.username}",
            color=discord.Color.red()
        )
        embed.add_field(name="ID", value=entry.user_id, inline=False)
        embed.add_field(name="Razón", value=entry.reason, inline=False)
        embed.add_field(name="Fecha", value=entry.created_at, inline=False)

        if entry.proofs:
            embed.add_field(name="Pruebas", value="\n".join(entry.proofs), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================================================
    # /blacklist list
    # ============================================================

    @app_commands.command(name="blacklist_list", description="Lista completa de la blacklist global.")
    async def blacklist_list(self, interaction: discord.Interaction):

        if not is_staff(interaction.user.id):
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        if not self.blacklist:
            return await interaction.response.send_message("📭 La blacklist está vacía.", ephemeral=True)

        embed = discord.Embed(
            title="Lista de blacklist global",
            color=discord.Color.dark_red()
        )

        desc = ""
        for uid, data in self.blacklist.items():
            entry = BlacklistEntry.from_dict(data)
            desc += f"**{entry.username}** (`{entry.user_id}`)\nRazón: {entry.reason}\n\n"

        embed.description = desc[:4000]

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ============================================================
    # AUTO-BAN AL ENTRAR
    # ============================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):

        if member.guild.id in EXCLUDED_GUILDS:
            return

        if self.is_blacklisted(member.id):
            try:
                await member.guild.ban(
                    member,
                    reason="[GLOBAL BLACKLIST] Intento de entrar estando en blacklist.",
                    delete_message_days=0
                )
            except:
                pass


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(GlobalBlacklistCog(bot))
