from fastapi import APIRouter, HTTPException, Request
from db import get_pool
from auth import get_current_user, SUPABASE_URL, SUPABASE_ANON_KEY
from models import UsernameUpdate
import httpx
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]

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
        raise HTTPException(status_code=401, detail="Invalid token")

    sb_user = resp.json()
    supabase_uid = sb_user.get("id")
    email = sb_user.get("email", "")
    metadata = sb_user.get("user_metadata", {})
    name = metadata.get("full_name", "") or metadata.get("name", "") or email.split("@")[0]
    picture = metadata.get("avatar_url", "") or metadata.get("picture", "")

    pool = get_pool()

    # Check by supabase_uid
    existing = await pool.fetchrow(
        "SELECT user_id, email, name, picture, username, "
        "to_char(join_date, 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as join_date "
        "FROM users WHERE supabase_uid = $1",
        supabase_uid
    )
    if existing:
        await pool.execute(
            "UPDATE users SET name = $1, picture = $2 WHERE supabase_uid = $3",
            name, picture, supabase_uid
        )
        updated = await pool.fetchrow(
            "SELECT user_id, email, name, picture, username, "
            "to_char(join_date, 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as join_date "
            "FROM users WHERE supabase_uid = $1",
            supabase_uid
        )
        return dict(updated)

    # Check by email (for migrated users)
    existing_by_email = await pool.fetchrow(
        "SELECT user_id FROM users WHERE email = $1 AND supabase_uid IS NULL",
        email
    )
    if existing_by_email:
        await pool.execute(
            "UPDATE users SET supabase_uid = $1, name = $2, picture = $3 WHERE email = $4",
            supabase_uid, name, picture, email
        )
        updated = await pool.fetchrow(
            "SELECT user_id, email, name, picture, username, "
            "to_char(join_date, 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as join_date "
            "FROM users WHERE email = $1",
            email
        )
        return dict(updated)

    # New user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    username = (name.lower().replace(" ", "")[:12] + user_id[-4:])

    await pool.execute(
        """INSERT INTO users (user_id, supabase_uid, email, name, picture, username)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        user_id, supabase_uid, email, name, picture, username
    )

    row = await pool.fetchrow(
        "SELECT user_id, email, name, picture, username, "
        "to_char(join_date, 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as join_date "
        "FROM users WHERE user_id = $1",
        user_id
    )
    return dict(row)


@router.get("/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return user


@router.post("/logout")
async def logout():
    return {"message": "Logged out"}


@router.put("/profile")
async def update_profile(body: UsernameUpdate, request: Request):
    user = await get_current_user(request)
    username = body.username.strip().lower()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    pool = get_pool()
    existing = await pool.fetchrow(
        "SELECT user_id FROM users WHERE username = $1 AND user_id != $2",
        username, user["user_id"]
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    await pool.execute(
        "UPDATE users SET username = $1 WHERE user_id = $2",
        username, user["user_id"]
    )
    row = await pool.fetchrow(
        "SELECT user_id, email, name, picture, username, "
        "to_char(join_date, 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as join_date "
        "FROM users WHERE user_id = $1",
        user["user_id"]
    )
    return dict(row)
