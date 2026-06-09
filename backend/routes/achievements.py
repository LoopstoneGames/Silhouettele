import operator as _op
from fastapi import APIRouter, Request
from db import get_pool
from auth import get_current_user

router = APIRouter(prefix="/achievements", tags=["achievements"])

ACHIEVEMENTS = [
    {"id": "first_solve", "name": "First Steps", "description": "Solve your first puzzle", "icon": "award", "condition": "puzzles_solved >= 1"},
    {"id": "solver_10", "name": "Getting Warmer", "description": "Solve 10 puzzles", "icon": "flame", "condition": "puzzles_solved >= 10"},
    {"id": "solver_25", "name": "Architecture Buff", "description": "Solve 25 puzzles", "icon": "building-2", "condition": "puzzles_solved >= 25"},
    {"id": "solver_50", "name": "Master Builder", "description": "Solve 50 puzzles", "icon": "crown", "condition": "puzzles_solved >= 50"},
    {"id": "streak_5", "name": "On Fire", "description": "Achieve a 5-day streak", "icon": "zap", "condition": "longest_streak >= 5"},
    {"id": "streak_10", "name": "Unstoppable", "description": "Achieve a 10-day streak", "icon": "rocket", "condition": "longest_streak >= 10"},
    {"id": "streak_30", "name": "Legend", "description": "Achieve a 30-day streak", "icon": "star", "condition": "longest_streak >= 30"},
    {"id": "perfect_1", "name": "Bullseye", "description": "Solve a puzzle in 1 guess", "icon": "target", "condition": "perfect_solves >= 1"},
    {"id": "perfect_5", "name": "Sharpshooter", "description": "Get 5 perfect solves", "icon": "crosshair", "condition": "perfect_solves >= 5"},
    {"id": "perfect_10", "name": "Globe Trotter", "description": "Get 10 perfect solves", "icon": "globe", "condition": "perfect_solves >= 10"},
]

_OPS = {">=": _op.ge, "<=": _op.le, "==": _op.eq, ">": _op.gt, "<": _op.lt}


def _parse_condition(cond_str: str):
    parts = cond_str.split()
    if len(parts) != 3 or parts[1] not in _OPS:
        raise ValueError(f"Invalid achievement condition: {cond_str!r}")
    return parts[0], _OPS[parts[1]], int(parts[2])


# Parse once at import — a malformed condition crashes at startup, not mid-request.
_PARSED_CONDITIONS = [_parse_condition(a["condition"]) for a in ACHIEVEMENTS]


def _check_achievements(stats: dict) -> list:
    earned = []
    for a, (field, op_fn, val) in zip(ACHIEVEMENTS, _PARSED_CONDITIONS):
        if op_fn(stats.get(field, 0) or 0, val):
            earned.append(a["id"])
    return earned


@router.get("/me")
async def get_my_achievements(request: Request):
    user = await get_current_user(request)
    pool = get_pool()

    row = await pool.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user["user_id"])
    stats = dict(row) if row else {
        "puzzles_solved": 0, "longest_streak": 0, "perfect_solves": 0,
        "current_streak": 0, "puzzles_played": 0, "total_guesses": 0
    }

    earned_ids = _check_achievements(stats)

    notif_row = await pool.fetchrow(
        "SELECT notified FROM achievement_notifications WHERE user_id = $1",
        user["user_id"]
    )
    notified_ids = list(notif_row["notified"]) if notif_row and notif_row["notified"] else []
    new_badges = [aid for aid in earned_ids if aid not in notified_ids]

    result = []
    for a in ACHIEVEMENTS:
        result.append({
            **a,
            "earned": a["id"] in earned_ids,
            "is_new": a["id"] in new_badges,
        })

    if new_badges:
        all_notified = list(set(notified_ids + new_badges))
        await pool.execute(
            """INSERT INTO achievement_notifications (user_id, notified)
               VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET notified = $2""",
            user["user_id"], all_notified
        )

    return {"achievements": result, "earned_count": len(earned_ids), "total_count": len(ACHIEVEMENTS)}
