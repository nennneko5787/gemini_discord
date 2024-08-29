import asyncpg

class Database:
    pool: asyncpg.Pool = None
    
    @classmethod
    async def connect(cls)
        cls.pool = await asyncpg.create_pool(os.getenv("dsn"))