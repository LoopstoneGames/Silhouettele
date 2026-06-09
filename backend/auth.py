from fastapi import HTTPException, Request
from db import get_pool
import httpx
import os
import time
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_ANON_KEY = os.environ['SUPABASE_ANON_KEY']

# Short-lived in-process cache so each request doesn't hit Supabase's auth API.
# TTL of 60s means at most 60s of stale profile data after a name/picture update.
_TOKEN_CACHE: dict = {}
_TOKEN_CACHE_TTL = 60
_TOKEN_CACHE_MAX = 500


def _cache_get(token: str):
    entry = _TOKEN_CACHE.get(token)
    if entry and entry[1] > time.monotonic():
        return entry[0]
    return None


def _cache_set(token: str, user: dict) -> None:
    if len(_TOKEN_CACHE) >= _TOKEN_CACHE_MAX:
        now = time.monotonic()
        expired = [k for k, v in _TOKEN_CACHE.items() if v[1] <= now]
        for k in (expired if expired else [next(iter(_TOKEN_CACHE))]):
            _TOKEN_CACHE.pop(k, None)
    _TOKEN_CACHE[token] = (user, time.monotonic() + _TOKEN_CACHE_TTL)


async def get_current_user(request: Request) -> dict:
    """Validate token by calling Supabase's auth API, then look up app user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]

    cached = _cache_get(token)
    if cached:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY,
            },
            timeout=10,
        )

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    elif resp.status_code != 200:
        # Rate-limit, Supabase outage, etc. — don't silently downgrade to guest.
        raise HTTPException(status_code=503, detail="Authentication service unavailable")

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

    user = dict(row)
    _cache_set(token, user)
    return user


async def get_user_or_guest(request: Request) -> dict:
    try:
        user = await get_current_user(request)
        user["is_guest"] = False
        return user
    except HTTPException as exc:
        # Only fall back to guest for genuine "no / invalid token" errors.
        # Re-raise 503 (Supabase outage) and any other unexpected status so
        # a valid-token request is never silently re-attributed to a guest.
        if exc.status_code != 401:
            raise

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
