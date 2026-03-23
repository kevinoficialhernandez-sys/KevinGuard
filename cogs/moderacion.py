import discord
from discord.ext import commands
from discord import app_commands

class Moderacion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ============================
    # BAN
    # ============================

    @app_commands.command(name="ban", description="Banea a un usuario del servidor.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):
        if usuario == interaction.user:
            return await interaction.response.send_message("❌ No puedes banearte a ti mismo.", ephemeral=True)

        if usuario.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ No puedes banear a alguien con un rol igual o superior.", ephemeral=True)

        await usuario.ban(reason=razon)

        embed = discord.Embed(
            title="🔨 Usuario Baneado",
            description=f"**{usuario}** ha sido baneado.\n**Razón:** {razon}",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    # ============================
    # UNBAN
    # ============================

    @app_commands.command(name="unban", description="Desbanea a un usuario por ID.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):

        try:
            user = await self.bot.fetch_user(int(user_id))
        except:
            return await interaction.response.send_message("❌ ID inválida.", ephemeral=True)

        bans = await interaction.guild.bans()
        banned_users = [ban_entry.user for ban_entry in bans]

        if user not in banned_users:
            return await interaction.response.send_message("❌ Ese usuario no está baneado.", ephemeral=True)

        await interaction.guild.unban(user)

        embed = discord.Embed(
            title="🔓 Usuario Desbaneado",
            description=f"**{user}** ha sido desbaneado.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    # ============================
    # KICK
    # ============================

    @app_commands.command(name="kick", description="Expulsa a un usuario del servidor.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "Sin razón"):

        if usuario == interaction.user:
            return await interaction.response.send_message("❌ No puedes expulsarte a ti mismo.", ephemeral=True)

        if usuario.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ No puedes expulsar a alguien con un rol igual o superior.", ephemeral=True)

        await usuario.kick(reason=razon)

        embed = discord.Embed(
            title="👢 Usuario Expulsado",
            description=f"**{usuario}** ha sido expulsado.\n**Razón:** {razon}",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    # ============================
    # MUTE
    # ============================

    @app_commands.command(name="mute", description="Mutea a un usuario asignándole el rol 'Muted'.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, usuario: discord.Member, minutos: int = 10):

        if usuario == interaction.user:
            return await interaction.response.send_message("❌ No puedes mutearte a ti mismo.", ephemeral=True)

        duration = discord.utils.utcnow() + discord.timedelta(minutes=minutos)

        try:
            await usuario.timeout(duration)
        except:
            return await interaction.response.send_message("❌ No pude mutear al usuario. Revisa mis permisos.", ephemeral=True)

        embed = discord.Embed(
            title="🔇 Usuario Muteado",
            description=f"**{usuario}** ha sido muteado por **{minutos} minutos**.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    # ============================
    # UNMUTE
    # ============================

    @app_commands.command(name="unmute", description="Desmutea a un usuario.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, usuario: discord.Member):

        try:
            await usuario.timeout(None)
        except:
            return await interaction.response.send_message("❌ No pude desmutear al usuario.", ephemeral=True)

        embed = discord.Embed(
            title="🔊 Usuario Desmuteado",
            description=f"**{usuario}** ha sido desmuteado.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderacion(bot))
