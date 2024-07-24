import asyncio
import os

if os.path.isfile(".env"):
    from dotenv import load_dotenv

    load_dotenv()


class GeminiAPIKey:
    def __init__(self, key: str):
        self.key = key
        self.limit = 2

    async def wait(self):
        print(f"APIKey {self.key} is waiting now")
        await asyncio.sleep(60)
        self.limit = 2
        print("waited")
