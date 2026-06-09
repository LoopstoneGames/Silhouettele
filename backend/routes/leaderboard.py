from fastapi import APIRouter, Request
from db import get_pool
from auth import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

_METRIC_COLS = {
    "puzzles_solved": "puzzles_solved",
    "current_streak": "current_streak",
    "longest_streak": "longest_streak",
    "perfect_solves": "perfect_solves",
}


@router.get("/overall")
async def get_overall_leaderboard(metric: str = "puzzles_solved", request: Request = None):
    user = await get_current_user(request)
    col = _METRIC_COLS.get(metric, "puzzles_solved")

    pool = get_pool()
    rows = await pool.fetch(
        f"""SELECT us.*, u.user_id, u.username, u.name, u.picture
            FROM user_stats us
            JOIN users u ON us.user_id = u.user_id
            ORDER BY us.{col} DESC
            LIMIT 100"""
    )

    leaderboard = []
    for i, r in enumerate(rows):
        solved = r["puzzles_solved"] or 0
        total_g = r["total_guesses"] or 0
        leaderboard.append({
            "rank": i + 1,
            "user_id": r["user_id"],
            "username": r["username"] or r["name"] or "Unknown",
            "name": r["name"] or "Unknown",
            "picture": r["picture"] or "",
            "puzzles_solved": solved,
            "current_streak": r["current_streak"] or 0,
            "longest_streak": r["longest_streak"] or 0,
            "perfect_solves": r["perfect_solves"] or 0,
            "avg_guesses": round(total_g / solved, 1) if solved > 0 else 0,
            "is_me": r["user_id"] == user["user_id"],
        })
    return leaderboard


@router.get("/friends")
async def get_friends_leaderboard(metric: str = "puzzles_solved", request: Request = None):
    user = await get_current_user(request)
    col = _METRIC_COLS.get(metric, "puzzles_solved")

    pool = get_pool()
    friend_rows = await pool.fetch(
        """SELECT CASE WHEN user_id = $1 THEN friend_id ELSE user_id END as fid
           FROM friendships
           WHERE (user_id = $1 OR friend_id = $1) AND status = 'accepted'""",
        user["user_id"]
    )
    friend_ids = [user["user_id"]] + [r["fid"] for r in friend_rows]

    rows = await pool.fetch(
        f"""SELECT us.*, u.user_id, u.username, u.name, u.picture
            FROM user_stats us
            JOIN users u ON us.user_id = u.user_id
            WHERE us.user_id = ANY($1)
            ORDER BY us.{col} DESC""",
        friend_ids
    )

    leaderboard = []
    for i, r in enumerate(rows):
        solved = r["puzzles_solved"] or 0
        total_g = r["total_guesses"] or 0
        leaderboard.append({
            "rank": i + 1,
            "user_id": r["user_id"],
            "username": r["username"] or r["name"] or "Unknown",
            "name": r["name"] or "Unknown",
            "picture": r["picture"] or "",
            "puzzles_solved": solved,
            "current_streak": r["current_streak"] or 0,
            "longest_streak": r["longest_streak"] or 0,
            "perfect_solves": r["perfect_solves"] or 0,
            "avg_guesses": round(total_g / solved, 1) if solved > 0 else 0,
            "is_me": r["user_id"] == user["user_id"],
        })
    return leaderboard
