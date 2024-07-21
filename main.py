import os

import discord
from discord.ext import commands
from keep_alive import keep_alive

if os.path.isfile(".env"):
    from dotenv import load_dotenv

    load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot("owo#", intents=intents)


@bot.event
async def setup_hook():
    await bot.load_extension("cogs.aichat")


keep_alive()
bot.run(os.getenv("discord"))
