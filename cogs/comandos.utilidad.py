import discord
from discord.ext import commands
from discord import app_commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="say",
        description="El bot enviará un mensaje con el contenido que escribas."
    )
    async def say(self, interaction: discord.Interaction, mensaje: str):
        # Borra el mensaje del slash command
        await interaction.response.send_message("Mensaje enviado.", ephemeral=True)

        # Envía el mensaje al canal donde se usó el comando
        await interaction.channel.send(mensaje)


async def setup(bot):
    await bot.add_cog(Say(bot))
