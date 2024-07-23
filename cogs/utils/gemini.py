import asyncio
import json
import traceback
from typing import List
import random

import aiohttp


class Gemini:
    @classmethod
    async def stream(
        cls,
        content: str,
        apiKeys: List[str],
        history: List[dict] = None,
        model: str = "gemini-1.5-pro",
        proxies: List[str] = None,
    ) -> str:
        count = 0
        maxcount = len(apiKeys)

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if not history:
            history = list()

        contents = history
        contents.append(
            {
                "parts": [
                    {
                        "text": content,
                    },
                ],
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
                try:
                    async with session.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={apiKey}",
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
                except:
                    traceback.print_exc()
                    count += 1
                asyncio.sleep(2)
            response.raise_for_status()


async def main():
    print("result", await Gemini.stream("こんにちは"))


if __name__ == "__main__":
    asyncio.run(main())
