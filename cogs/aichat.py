import json
import os
import traceback
from collections import defaultdict

import aiohttp
import asyncpg
import discord
from discord.ext import commands

from .utils import Gemini, GeminiAPIKey

if os.path.isfile(".env"):
    from dotenv import load_dotenv

    load_dotenv()


class AIChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot, *, proxies: dict):
        self.bot: commands.Bot = bot
        self.chatHistories: dict = defaultdict(list)
        self.apiKeys = [GeminiAPIKey(os.getenv(f"gemini{i}")) for i in range(5)]
        self.proxies = [
            f"{proxy.get('protocols', [])[0]}://{proxy.get('ip')}:{proxy.get('port')}"
            for proxy in proxies.get("data", [])
        ]
        print("AIChatCog loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        self.pool: asyncpg.Pool = await asyncpg.create_pool(
            os.getenv("dsn"), statement_cache_size=0
        )
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM users")
            for row in rows:
                self.chatHistories[row["id"]] = json.loads(row["data"])
        print("Database connected and chat histories loaded.")

    @commands.hybrid_command(
        name="delmsghistory", description="Geminiとのメッセージ履歴を削除します。"
    )
    async def delmsghistory(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        self.chatHistories[ctx.author.id] = []
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (id, data)
                    VALUES ($1, $2)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        data = EXCLUDED.data
                    """,
                    ctx.author.id,
                    json.dumps(self.chatHistories[ctx.author.id]),
                )
        except Exception as e:
            traceback.print_exc()
            await ctx.send("エラーが発生しました。", ephemeral=True)
        else:
            await ctx.send("メッセージ履歴を消去しました。", ephemeral=True)

    def splitContent(self, content, maxLength=2000):
        parts = []
        while len(content) > maxLength:
            splitPoint = maxLength
            while splitPoint > 0 and not content[splitPoint].isspace():
                splitPoint -= 1
            if splitPoint == 0:
                splitPoint = maxLength
            part = content[:splitPoint].strip()
            parts.append(part)
            content = content[splitPoint:].strip()
        if content:
            parts.append(content)
        return parts

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (
            message.channel.id != 1265578414572572702
            or message.author.bot
            or message.author.system
        ):
            return
        async with message.channel.typing():
            try:
                content = await Gemini.chat(
                    message.clean_content,
                    apiKeys=self.apiKeys,
                    history=self.chatHistories[message.author.id],
                    files=message.attachments,
                    proxies=None,
                )
            except Exception as e:
                traceback.print_exc()
                await message.reply("Error")
                return
            self.chatHistories[message.author.id].append(
                {"parts": [{"text": message.clean_content}], "role": "user"}
            )
            self.chatHistories[message.author.id].append(
                {"parts": [{"text": content}], "role": "model"}
            )
            contents = self.splitContent(content)
            for c in contents:
                await message.reply(c)

            try:
                async with self.pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO users (id, data)
                        VALUES ($1, $2)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            data = EXCLUDED.data
                        """,
                        message.author.id,
                        json.dumps(self.chatHistories[message.author.id]),
                    )
            except Exception as e:
                traceback.print_exc()


async def setup(bot: commands.Bot):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
        ) as response:
            proxies = await response.json()
            await bot.add_cog(AIChatCog(bot, proxies=proxies))
