import asyncio
import json
import os
import random
import traceback
from collections import defaultdict

import aiohttp
import asyncpg
import discord
from discord.ext import commands

from .dbservice import Database
from .utils import Gemini, GeminiAPIKey

if os.path.isfile(".env"):
    from dotenv import load_dotenv

    load_dotenv()


class AIChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.loaded = False
        self.model: dict = defaultdict(str)
        self.chatHistories: dict = defaultdict(list)
        self.chatHistoriesNSFW: dict = defaultdict(list)
        self.apiKeys = [GeminiAPIKey(os.getenv(f"gemini{i}")) for i in range(20)]
        print(len(self.apiKeys))
        self.waitList = []
        print("AIChatCog loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        rows = await Database.pool.fetch("SELECT * FROM users")
        for row in rows:
            self.model[row["id"]] = row["model"]
            self.chatHistories[row["id"]] = json.loads(row["data"])
            self.chatHistoriesNSFW[row["id"]] = json.loads(row["data_nsfw"])
        print("Database connected and chat histories loaded.")
        self.loaded = True

    @commands.hybrid_command(
        name="model", description="Geminiのモデルを変更します。"
    )
    async def modelCommand(self, ctx: commands.Context, model: str = "gemini-1.5-pro-exp-0827"):
        await ctx.defer(ephemeral=True)
        if not self.loaded:
            await ctx.send("データベースの初期化が終わっていません", ephemeral=True)
        self.model[ctx.author.id] = model
        try:
            await Database.pool.execute(
                """
                    INSERT INTO users (id, model)
                    VALUES ($1, $2)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        model = EXCLUDED.model
                """,
                ctx.author.id,
                model,
            )
        except Exception as e:
            traceback.print_exc()
            await ctx.send("エラーが発生しました。", ephemeral=True)
        else:
            await ctx.send("モデルを変更しました。", ephemeral=True)

    @commands.hybrid_command(
        name="clear", description="Geminiとのメッセージ履歴を削除します。"
    )
    async def clearCommand(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        if not self.loaded:
            await ctx.send("データベースの初期化が終わっていません", ephemeral=True)
        self.chatHistories[ctx.author.id] = []
        try:
            await Database.pool.execute(
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

    @commands.hybrid_command(
        name="clearnsfw", description="NSFW Geminiとのメッセージ履歴を削除します。"
    )
    async def clearNSFWCommand(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        if not self.loaded:
            await ctx.send("データベースの初期化が終わっていません", ephemeral=True)
        self.chatHistoriesNSFW[ctx.author.id] = []
        try:
            await Database.pool.execute(
                """
                    INSERT INTO users (id, data_nsfw)
                    VALUES ($1, $2)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        data = EXCLUDED.data
                """,
                ctx.author.id,
                json.dumps(self.chatHistoriesNSFW[ctx.author.id]),
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
            message.channel.id != 1264471909903368338
            and message.channel.id != 1265578414572572702
            or message.author.bot
            or message.author.system
            or not self.loaded
        ):
            return
        if message.author.id in self.waitList:
            await message.reply("メッセージ生成を待つ必要があります。")
            return
        if message.channel.id == 1264471909903368338:
            history = self.chatHistories[message.author.id]
        else:
            history = self.chatHistoriesNSFW[message.author.id]
        self.waitList.append(message.author.id)
        try:
            async with message.channel.typing():
                try:
                    random.shuffle(self.apiKeys)
                    content = await Gemini.chat(
                        message.clean_content,
                        apiKeys=self.apiKeys,
                        history=history,
                        files=message.attachments,
                        model=self.model[message.author.id],
                        proxies=None,
                    )
                except Exception as e:
                    traceback.print_exc()
                    await message.reply("Error")
                    return
                print(content)
                contents = self.splitContent(content)
                for c in contents:
                    await message.reply(c)
                history.append(
                    {"parts": [{"text": message.clean_content}], "role": "user"}
                )
                history.append(
                    {"parts": [{"text": content}], "role": "model"}
                )
            try:
                await Database.pool.execute(
                    f"""
                        INSERT INTO users (id, {"data " if message.channel.id == 1264471909903368338 else "data_nsfw"})
                        VALUES ($1, $2)
                        ON CONFLICT (id)
                        DO UPDATE SET
                            data = EXCLUDED.data
                    """,
                    message.author.id,
                    json.dumps(history),
                )
            except Exception as e:
                traceback.print_exc()
        finally:
            self.waitList.remove(message.author.id)


async def setup(bot: commands.Bot):
    async with aiohttp.ClientSession() as session:
        await bot.add_cog(AIChatCog(bot))
