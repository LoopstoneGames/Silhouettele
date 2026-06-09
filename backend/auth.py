from fastapi import HTTPException, Request
from db import get_pool
import httpx
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_ANON_KEY = os.environ['SUPABASE_ANON_KEY']


async def get_current_user(request: Request) -> dict:
    """Validate token by calling Supabase's auth API, then look up app user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]

    # Verify token with Supabase
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY,
            },
            timeout=10,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    sb_user = resp.json()
    supabase_uid = sb_user.get("id")
    if not supabase_uid:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    pool = get_pool()
    row = await pool.fetchrow(
        "SELECT user_id, email, name, picture, username, "
        "to_char(join_date, 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as join_date "
        "FROM users WHERE supabase_uid = $1",
        supabase_uid
    )
    if not row:
        raise HTTPException(status_code=401, detail="User not registered")

    return dict(row)


async def get_user_or_guest(request: Request) -> dict:
    try:
        user = await get_current_user(request)
        user["is_guest"] = False
        return user
    except HTTPException:
        pass

    guest_id = request.headers.get("X-Guest-ID")
    if not guest_id:
        raise HTTPException(status_code=401, detail="Not authenticated and no guest ID")

    return {
        "user_id": f"guest_{guest_id}",
        "email": "",
        "name": "Guest",
        "picture": "",
        "username": "guest",
        "is_guest": True,
    }
