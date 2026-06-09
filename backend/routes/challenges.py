from fastapi import APIRouter, Request
from db import get_pool
from auth import get_current_user
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/challenges", tags=["challenges"])


def _get_week_range():
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _get_month_range():
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = now.replace(year=now.year + 1, month=1, day=1) - timedelta(seconds=1)
    else:
        end = now.replace(month=now.month + 1, day=1) - timedelta(seconds=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _date_range(start_str, end_str):
    dates = []
    d = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    while d <= end:
        dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return dates


@router.get("/current")
async def get_current_challenges(request: Request):
    user = await get_current_user(request)
    pool = get_pool()

    week_start, week_end = _get_week_range()
    month_start, month_end = _get_month_range()
    week_dates = _date_range(week_start, week_end)
    month_dates = _date_range(month_start, month_end)

    week_rows = await pool.fetch(
        "SELECT puzzle_date, is_correct FROM guesses "
        "WHERE user_id = $1 AND puzzle_date = ANY($2)",
        user["user_id"], week_dates
    )
    week_solved = {r["puzzle_date"] for r in week_rows if r["is_correct"]}
    week_days = len({r["puzzle_date"] for r in week_rows})
    week_total = len(week_rows)

    month_rows = await pool.fetch(
        "SELECT puzzle_date, is_correct FROM guesses "
        "WHERE user_id = $1 AND puzzle_date = ANY($2)",
        user["user_id"], month_dates
    )
    month_solved = len({r["puzzle_date"] for r in month_rows if r["is_correct"]})
    month_total = len(month_rows)
    month_avg = round(month_total / month_solved, 1) if month_solved > 0 else 0

    return {
        "weekly": {
            "type": "weekly",
            "title": "Weekly Challenge",
            "period": f"{week_start} to {week_end}",
            "week_start": week_start, "week_end": week_end,
            "goals": [
                {"label": "Puzzles Solved", "current": len(week_solved), "target": 7, "complete": len(week_solved) >= 7},
                {"label": "Days Played", "current": week_days, "target": 7, "complete": week_days >= 7},
            ],
            "score": len(week_solved) * 100 + max(0, (50 - week_total)) * 5,
        },
        "monthly": {
            "type": "monthly",
            "title": "Monthly Challenge",
            "period": f"{month_start} to {month_end}",
            "month_start": month_start, "month_end": month_end,
            "goals": [
                {"label": "Puzzles Solved", "current": month_solved, "target": 20, "complete": month_solved >= 20},
                {"label": "Avg Guesses", "current": month_avg, "target": 3.0, "complete": month_avg > 0 and month_avg <= 3.0},
            ],
            "score": month_solved * 50 + (100 if month_avg > 0 and month_avg <= 3.0 else 0),
        },
    }


@router.get("/leaderboard")
async def get_challenge_leaderboard(challenge_type: str = "weekly", request: Request = None):
    user = await get_current_user(request)

    if challenge_type == "weekly":
        start, end = _get_week_range()
    else:
        start, end = _get_month_range()

    dates = _date_range(start, end)
    pool = get_pool()

    rows = await pool.fetch(
        """SELECT g.user_id, u.username, u.name, u.picture,
                  COUNT(DISTINCT CASE WHEN g.is_correct THEN g.puzzle_date END) as solved,
                  COUNT(*) as total_guesses
           FROM guesses g
           LEFT JOIN users u ON g.user_id = u.user_id
           WHERE g.puzzle_date = ANY($1)
           AND g.user_id NOT LIKE 'guest_%'
           GROUP BY g.user_id, u.username, u.name, u.picture
           ORDER BY solved DESC, total_guesses ASC
           LIMIT 50""",
        dates
    )

    leaderboard = []
    for i, r in enumerate(rows):
        solved = r["solved"] or 0
        score = solved * 100 + max(0, (50 - (r["total_guesses"] or 0))) * 5
        leaderboard.append({
            "rank": i + 1,
            "user_id": r["user_id"],
            "username": r["username"] or r["name"] or "Unknown",
            "name": r["name"] or "Unknown",
            "picture": r["picture"] or "",
            "solved": solved,
            "score": score,
            "is_me": r["user_id"] == user["user_id"],
        })
    return leaderboard
