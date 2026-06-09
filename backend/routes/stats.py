from fastapi import APIRouter, Request
from db import get_pool
from auth import get_current_user

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/me")
async def get_my_stats(request: Request):
    user = await get_current_user(request)
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user["user_id"])

    if not row:
        return {
            "user_id": user["user_id"],
            "puzzles_played": 0, "puzzles_solved": 0,
            "current_streak": 0, "longest_streak": 0,
            "total_guesses": 0, "perfect_solves": 0,
            "avg_guesses": 0,
        }

    stats = dict(row)
    solved = stats.get("puzzles_solved", 0)
    total_g = stats.get("total_guesses", 0)
    stats["avg_guesses"] = round(total_g / solved, 1) if solved > 0 else 0
    return stats
