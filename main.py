import discord
from discord.ext import commands
import os
import asyncio

# ============================
# TOKEN DESDE VARIABLE DE ENTORNO
# ============================

TOKEN = os.getenv("TOKEN")  # ← En tu hosting defines la variable TOKEN

if TOKEN is None:
    raise ValueError("❌ No se encontró la variable de entorno 'TOKEN'.")

# ============================
# INTENTS
# ============================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# ============================
# BOT
# ============================

bot = commands.Bot(command_prefix="!", intents=intents)

# ============================
# CARGAR TODOS LOS COGS AUTOMÁTICAMENTE
# ============================

async def load_cogs():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{file[:-3]}")
                print(f"[COG CARGADO] {file}")
            except Exception as e:
                print(f"[ERROR] No se pudo cargar {file}: {e}")

# ============================
# EVENTO ON_READY
# ============================

@bot.event
async def on_ready():
    print(f"Bot iniciado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

# ============================
# MAIN
# ============================

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())
