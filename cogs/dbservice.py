import os

import asyncpg

if os.path.isfile(".env"):
    from dotenv import load_dotenv

    load_dotenv()


class Database:
    pool: asyncpg.Pool = None

    @classmethod
    async def connect(cls):
        cls.pool = await asyncpg.create_pool(os.getenv("dsn"), statement_cache_size=0)
