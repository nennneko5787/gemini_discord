import asyncio
import base64
import json
import random
import traceback
from typing import List

import aiohttp
import aiohttp.client_exceptions
import discord

from .GeminiAPIKey import GeminiAPIKey


class Gemini:
    @classmethod
    async def chat(
        cls,
        content: str,
        apiKeys: List[GeminiAPIKey],
        history: List[dict] = None,
        files: List[discord.Attachment] = None,
        model: str = "gemini-1.5-pro-exp-0801",
        proxies: List[str] = None,
    ) -> str:
        count = 0
        maxcount = len(apiKeys)
        print(maxcount)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if not history:
            history = list()

        parts = []

        parts.append(
            {
                "text": content,
            }
        )

        if files:
            for file in files:
                mime = file.content_type
                rawData = await file.read()
                data = base64.b64encode(rawData).decode()
                parts.append(
                    {
                        "inlineData": {
                            "mimeType": mime,
                            "data": data,
                        },
                    }
                )

        contents = history
        contents.append(
            {
                "parts": parts,
                "role": "user",
            }
        )

        data: dict = {
            "contents": contents,
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE",
                },
            ],
        }

        async with aiohttp.ClientSession() as session:
            while count < maxcount:
                if proxies:
                    proxy = random.choice(proxies)
                else:
                    proxy = None
                apiKey = apiKeys[count]
                if apiKey.isWaiting:
                    print("apiKeyは現在待機中です")
                    count += 1
                    continue
                if apiKey.limit <= 0:
                    print("レートリミットに達しました")
                    asyncio.create_task(apiKey.wait())
                    count += 1
                    continue
                try:
                    async with session.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={apiKey.key}",
                        json=data,
                        headers=headers,
                        proxy=proxy,
                    ) as response:
                        response.raise_for_status()
                        byteList = []
                        async for line in response.content:
                            byteList.append(line)
                        data = b"".join(byteList).decode()
                        jsonData = json.loads(data)
                        responseList = []
                        for content in jsonData:
                            responseList.append(
                                content.get("candidates", [])[0]
                                .get("content", {})
                                .get("parts")[0]
                                .get("text")
                            )
                        return "".join(responseList)
                except aiohttp.client_exceptions.ClientResponseError as e:
                    traceback.print_exc()
                    if e.status == 429:
                        print("レートリミットに達した可能性があります...")
                        asyncio.create_task(apiKey.wait())
                        count += 1
                    else:
                        response.raise_for_status()
                except Exception:
                    traceback.print_exc()
                    asyncio.create_task(apiKey.wait())
                    count += 1


async def main():
    print(
        "result",
        await Gemini.chat(
            "こんにちは", apiKeys=[GeminiAPIKey(key="dummyKey", limit=10)]
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
