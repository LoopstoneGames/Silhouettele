import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

DATABASE_URL = os.environ['SUPABASE_DB_URL']

_pool: asyncpg.Pool = None


async def init_db():
    global _pool
    # statement_cache_size=0 is required for Supabase's pgbouncer connection pooler
    # which doesn't support prepared statements in transaction/statement pool mode
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
        statement_cache_size=0
    )


async def close_db():
    global _pool
    if _pool:
        await _pool.close()


def get_pool() -> asyncpg.Pool:
    return _pool
