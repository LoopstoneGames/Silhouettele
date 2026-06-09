import asyncio
import os
import sys
import asyncpg
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env')

async def main(email):
    conn = await asyncpg.connect(os.environ['SUPABASE_DB_URL'], statement_cache_size=0)
    row = await conn.fetchrow(
        "UPDATE auth.users SET email_confirmed_at = now() WHERE email = $1 RETURNING id, email, email_confirmed_at",
        email,
    )
    print("CONFIRMED:", dict(row) if row else None)
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
