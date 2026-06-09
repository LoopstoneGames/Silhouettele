from fastapi import APIRouter, HTTPException, Request
from db import get_pool
from models import FriendRequest
from auth import get_current_user
import uuid

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("/search")
async def search_users(q: str = "", request: Request = None):
    user = await get_current_user(request)
    if not q or len(q) < 2:
        return []
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT user_id, username, name, picture FROM users
           WHERE user_id != $1
           AND (username ILIKE $2 OR name ILIKE $2)
           LIMIT 20""",
        user["user_id"], f"%{q}%"
    )
    return [dict(r) for r in rows]


@router.post("/request")
async def send_friend_request(body: FriendRequest, request: Request):
    user = await get_current_user(request)
    if user["user_id"] == body.friend_user_id:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")
    pool = get_pool()
    existing = await pool.fetchrow(
        """SELECT friendship_id FROM friendships
           WHERE (user_id = $1 AND friend_id = $2) OR (user_id = $2 AND friend_id = $1)""",
        user["user_id"], body.friend_user_id
    )
    if existing:
        raise HTTPException(status_code=400, detail="Friendship already exists or pending")
    await pool.execute(
        """INSERT INTO friendships (friendship_id, user_id, friend_id, status)
           VALUES ($1, $2, $3, 'pending')""",
        str(uuid.uuid4()), user["user_id"], body.friend_user_id
    )
    return {"message": "Friend request sent"}


@router.post("/accept")
async def accept_friend(body: FriendRequest, request: Request):
    user = await get_current_user(request)
    pool = get_pool()
    tag = await pool.execute(
        """UPDATE friendships SET status = 'accepted'
           WHERE user_id = $1 AND friend_id = $2 AND status = 'pending'""",
        body.friend_user_id, user["user_id"]
    )
    if tag == "UPDATE 0":
        raise HTTPException(status_code=404, detail="No pending request found")
    return {"message": "Friend request accepted"}


@router.post("/decline")
async def decline_friend(body: FriendRequest, request: Request):
    user = await get_current_user(request)
    pool = get_pool()
    tag = await pool.execute(
        """DELETE FROM friendships
           WHERE user_id = $1 AND friend_id = $2 AND status = 'pending'""",
        body.friend_user_id, user["user_id"]
    )
    if tag == "DELETE 0":
        raise HTTPException(status_code=404, detail="No pending request found")
    return {"message": "Friend request declined"}


@router.delete("/{friend_user_id}")
async def remove_friend(friend_user_id: str, request: Request):
    user = await get_current_user(request)
    pool = get_pool()
    await pool.execute(
        """DELETE FROM friendships
           WHERE ((user_id = $1 AND friend_id = $2) OR (user_id = $2 AND friend_id = $1))
           AND status = 'accepted'""",
        user["user_id"], friend_user_id
    )
    return {"message": "Friend removed"}


@router.get("")
async def get_friends(request: Request):
    user = await get_current_user(request)
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT u.user_id, u.username, u.name, u.picture
           FROM friendships f
           JOIN users u ON u.user_id = CASE
               WHEN f.user_id = $1 THEN f.friend_id
               ELSE f.user_id
           END
           WHERE (f.user_id = $1 OR f.friend_id = $1) AND f.status = 'accepted'""",
        user["user_id"]
    )
    return [dict(r) for r in rows]


@router.get("/requests")
async def get_friend_requests(request: Request):
    user = await get_current_user(request)
    pool = get_pool()
    rows = await pool.fetch(
        """SELECT u.user_id, u.username, u.name, u.picture
           FROM friendships f
           JOIN users u ON u.user_id = f.user_id
           WHERE f.friend_id = $1 AND f.status = 'pending'""",
        user["user_id"]
    )
    return [dict(r) for r in rows]
