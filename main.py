import asyncio
import os
from contextlib import asynccontextmanager

import discord
from discord.ext import commands
from fastapi import FastAPI

from cogs.dbservice import Database

if os.path.isfile(".env"):
    from dotenv import load_dotenv

    load_dotenv()

discord.utils.setup_logging()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot("owo#", intents=intents)


@bot.event
async def setup_hook():
    await bot.load_extension("cogs.aichat")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Database.connect()
    asyncio.create_task(bot.start(os.getenv("discord")))
    yield
    await Database.pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return {
        "detail": "ok",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=10000)
