import discord
from discord.ext import commands
from discord import app_commands
import json
import os

WARN_FILE = os.path.join(os.path.dirname(__file__), "..", "warnings.json")


def load_warns():
    if not os.path.exists(WARN_FILE):
        with open(WARN_FILE, "w") as f:
            json.dump({}, f)
        return {}

    with open(WARN_FILE, "r") as f:
        return json.load(f)


def save_warns(data):
    with open(WARN_FILE, "w") as f:
        json.dump(data, f, indent=4)


class WarnSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # /warn
    # ============================

    @app_commands.command(
        name="warn",
        description="Da un warn a un usuario."
    )
    async def warn(self, interaction: discord.Interaction, usuario: discord.Member, razon: str):

        if usuario.bot:
            return await interaction.response.send_message("❌ No puedes warnear bots.", ephemeral=True)

        data = load_warns()
        guild_id = str(interaction.guild.id)
        user_id = str(usuario.id)

        if guild_id not in data:
            data[guild_id] = {}

        if user_id not in data[guild_id]:
            data[guild_id][user_id] = []

        data[guild_id][user_id].append(razon)
        save_warns(data)

        await interaction.response.send_message(
            f"⚠️ **Warn añadido a {usuario.mention}**\nRazón: `{razon}`",
            ephemeral=False
        )

    # ============================
    # /warnings
    # ============================

    @app_commands.command(
        name="warnings",
        description="Muestra los warns de un usuario."
    )
    async def warnings(self, interaction: discord.Interaction, usuario: discord.Member):

        data = load_warns()
        guild_id = str(interaction.guild.id)
        user_id = str(usuario.id)

        warns = data.get(guild_id, {}).get(user_id, [])

        if not warns:
            return await interaction.response.send_message(
                f"✅ {usuario.mention} **no tiene warns.**",
                ephemeral=False
            )

        texto = "\n".join([f"**{i+1}.** {w}" for i, w in enumerate(warns)])

        embed = discord.Embed(
            title=f"⚠️ Warnings de {usuario}",
            description=texto,
            color=discord.Color.blue()
        )

        await interaction.response.send_message(embed=embed)

    # ============================
    # /borrar_warn
    # ============================

    @app_commands.command(
        name="borrar_warn",
        description="Quita un warn por número a un usuario"
    )
    async def unwarn(self, interaction: discord.Interaction, usuario: discord.Member, numero: int):

        data = load_warns()
        guild_id = str(interaction.guild.id)
        user_id = str(usuario.id)

        warns = data.get(guild_id, {}).get(user_id, [])

        if not warns:
            return await interaction.response.send_message(
                f"❌ {usuario.mention} no tiene warns.",
                ephemeral=True
            )

        if numero < 1 or numero > len(warns):
            return await interaction.response.send_message(
                f"❌ Número inválido. Ese usuario solo tiene `{len(warns)}` warns.",
                ephemeral=True
            )

        eliminado = warns.pop(numero - 1)
        save_warns(data)

        await interaction.response.send_message(
            f"🗑️ **Warn #{numero} eliminado a {usuario.mention}**\nContenido: `{eliminado}`",
            ephemeral=False
        )


async def setup(bot):
    await bot.add_cog(WarnSystem(bot))
