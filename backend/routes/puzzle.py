from fastapi import APIRouter, HTTPException, Request
from db import get_pool
from auth import get_current_user, get_user_or_guest
from models import GuessRequest
from utils import (get_daily_building_id, get_today_str, get_building_by_id,
                   calculate_direction_distance, get_direction_arrow)
from data.buildings import BUILDINGS, SILHOUETTE_URLS
import uuid
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/puzzle", tags=["puzzle"])


async def _update_user_stats(pool, user_id: str, guess_number: int, puzzle_date: str):
    await pool.execute(
        """INSERT INTO user_stats
           (user_id, puzzles_played, puzzles_solved, total_guesses, perfect_solves,
            current_streak, longest_streak, last_solved_date)
           VALUES ($1, 0, 0, 0, 0, 0, 0, NULL)
           ON CONFLICT (user_id) DO NOTHING""",
        user_id
    )
    row = await pool.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    last_date = row["last_solved_date"]
    new_streak = (row["current_streak"] + 1) if last_date == yesterday else 1
    new_longest = max(row["longest_streak"], new_streak)
    new_perfect = row["perfect_solves"] + (1 if guess_number == 1 else 0)

    await pool.execute(
        """UPDATE user_stats SET
           puzzles_played = puzzles_played + 1,
           puzzles_solved = puzzles_solved + 1,
           total_guesses = total_guesses + $2,
           perfect_solves = $3,
           current_streak = $4,
           longest_streak = $5,
           last_solved_date = $6
           WHERE user_id = $1""",
        user_id, guess_number, new_perfect, new_streak, new_longest, puzzle_date
    )


async def _update_user_stats_failed(pool, user_id: str, puzzle_date: str):
    await pool.execute(
        """INSERT INTO user_stats
           (user_id, puzzles_played, puzzles_solved, total_guesses, perfect_solves,
            current_streak, longest_streak, last_solved_date)
           VALUES ($1, 0, 0, 0, 0, 0, 0, NULL)
           ON CONFLICT (user_id) DO NOTHING""",
        user_id
    )
    row = await pool.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)

    last_date = row["last_solved_date"]
    # last_solved_date is updated on both solves AND failures (see UPDATE below),
    # so this check reliably prevents double-counting on repeated calls.
    already_recorded = last_date == puzzle_date

    if not already_recorded:
        await pool.execute(
            """UPDATE user_stats SET
               puzzles_played = puzzles_played + 1,
               total_guesses = total_guesses + 6,
               current_streak = 0,
               last_solved_date = $2
               WHERE user_id = $1""",
            user_id, puzzle_date
        )


def _guess_select_cols():
    return ("guess_id, user_id, puzzle_date, guess_building_id, guess_building_name, "
            "guess_building_city, guess_building_country, guess_number, is_correct, "
            "direction, direction_arrow, distance_km")


@router.get("/today")
async def get_today_puzzle(request: Request):
    user = await get_user_or_guest(request)
    today = get_today_str()
    building_id = get_daily_building_id(today)
    building = get_building_by_id(building_id)

    pool = get_pool()
    rows = await pool.fetch(
        f"SELECT {_guess_select_cols()} FROM guesses "
        "WHERE user_id = $1 AND puzzle_date = $2 ORDER BY guess_number",
        user["user_id"], today
    )
    guesses = [dict(r) for r in rows]
    is_solved = any(g["is_correct"] for g in guesses)
    is_failed = len(guesses) >= 6 and not is_solved

    # Ensure failed stats are recorded even if the client never received the
    # response to the 6th-guess POST (tab closed, network drop, etc.).
    if is_failed and not user.get("is_guest"):
        await _update_user_stats_failed(pool, user["user_id"], today)

    result = {
        "puzzle_date": today,
        "guesses_used": len(guesses),
        "guesses_remaining": max(0, 6 - len(guesses)),
        "is_solved": is_solved,
        "is_failed": is_failed,
        "guesses": guesses,
        "silhouette_url": SILHOUETTE_URLS.get(building_id, "") if building else "",
        "is_guest": user.get("is_guest", False),
    }
    if is_solved or is_failed:
        result["building"] = building
    return result


@router.post("/guess")
async def submit_guess(body: GuessRequest, request: Request):
    user = await get_user_or_guest(request)
    today = get_today_str()
    correct_building_id = get_daily_building_id(today)
    correct_building = get_building_by_id(correct_building_id)

    guessed_building = get_building_by_id(body.building_id)
    if not guessed_building:
        raise HTTPException(status_code=400, detail="Building not in database")

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            rows = await conn.fetch(
                "SELECT guess_building_id, is_correct FROM guesses "
                "WHERE user_id = $1 AND puzzle_date = $2 FOR UPDATE",
                user["user_id"], today
            )
            existing = [dict(r) for r in rows]

            if any(g["is_correct"] for g in existing):
                raise HTTPException(status_code=400, detail="Already solved today's puzzle")
            if len(existing) >= 6:
                raise HTTPException(status_code=400, detail="No guesses left")
            if body.building_id in {g["guess_building_id"] for g in existing}:
                raise HTTPException(status_code=400, detail="You already guessed this building today")

            is_correct = body.building_id == correct_building_id
            direction, distance = calculate_direction_distance(
                guessed_building["latitude"], guessed_building["longitude"],
                correct_building["latitude"], correct_building["longitude"]
            )
            guess_number = len(existing) + 1

            guess_doc = {
                "guess_id": str(uuid.uuid4()),
                "user_id": user["user_id"],
                "puzzle_date": today,
                "guess_building_id": body.building_id,
                "guess_building_name": guessed_building["name"],
                "guess_building_city": guessed_building["city"],
                "guess_building_country": guessed_building["country"],
                "guess_number": guess_number,
                "is_correct": is_correct,
                "direction": direction if not is_correct else "",
                "direction_arrow": get_direction_arrow(direction) if not is_correct else "",
                "distance_km": distance if not is_correct else 0,
            }

            await conn.execute(
                """INSERT INTO guesses
                   (guess_id, user_id, puzzle_date, guess_building_id, guess_building_name,
                    guess_building_city, guess_building_country, guess_number, is_correct,
                    direction, direction_arrow, distance_km)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
                guess_doc["guess_id"], guess_doc["user_id"], guess_doc["puzzle_date"],
                guess_doc["guess_building_id"], guess_doc["guess_building_name"],
                guess_doc["guess_building_city"], guess_doc["guess_building_country"],
                guess_doc["guess_number"], guess_doc["is_correct"],
                guess_doc["direction"], guess_doc["direction_arrow"], guess_doc["distance_km"]
            )

    if not user.get("is_guest"):
        if is_correct:
            await _update_user_stats(pool, user["user_id"], guess_number, today)
        elif guess_number >= 6:
            await _update_user_stats_failed(pool, user["user_id"], today)

    all_rows = await pool.fetch(
        f"SELECT {_guess_select_cols()} FROM guesses "
        "WHERE user_id = $1 AND puzzle_date = $2 ORDER BY guess_number",
        user["user_id"], today
    )
    all_guesses = [dict(r) for r in all_rows]

    is_solved = is_correct
    is_failed = guess_number >= 6 and not is_correct
    result = {
        "guess": guess_doc,
        "guesses_used": guess_number,
        "guesses_remaining": max(0, 6 - guess_number),
        "is_solved": is_solved,
        "is_failed": is_failed,
        "guesses": all_guesses,
    }
    if is_solved or is_failed:
        result["building"] = correct_building
    return result


@router.get("/share")
async def get_share_text(request: Request):
    user = await get_user_or_guest(request)
    today = get_today_str()

    pool = get_pool()
    rows = await pool.fetch(
        "SELECT is_correct, direction, distance_km FROM guesses "
        "WHERE user_id = $1 AND puzzle_date = $2 ORDER BY guess_number",
        user["user_id"], today
    )
    guesses = [dict(r) for r in rows]

    if not guesses:
        raise HTTPException(status_code=400, detail="No guesses to share")

    is_solved = any(g["is_correct"] for g in guesses)
    score = f"{len(guesses)}/6" if is_solved else "X/6"
    lines = [f"Silhouettele {today} {score}", ""]

    for g in guesses:
        if g["is_correct"]:
            lines.append("\u2705")
        else:
            arrow = get_direction_arrow(g.get("direction", "")) or "?"
            dist = g.get("distance_km", 0)
            if dist < 500:
                bar = "\u2588\u2588\u2588\u2588"
            elif dist < 2000:
                bar = "\u2588\u2588\u2588\u2591"
            elif dist < 5000:
                bar = "\u2588\u2588\u2591\u2591"
            else:
                bar = "\u2588\u2591\u2591\u2591"
            lines.append(f"{bar} {arrow} {dist:,} km")

    lines.extend(["", "Play at silhouettele.cc"])
    return {"share_text": "\n".join(lines), "is_solved": is_solved, "score": score}


@router.get("/calendar")
async def get_puzzle_calendar(request: Request):
    user = await get_current_user(request)
    pool = get_pool()

    date_list = [
        (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(30)
    ]

    rows = await pool.fetch(
        "SELECT puzzle_date, is_correct FROM guesses WHERE user_id = $1 AND puzzle_date = ANY($2)",
        user["user_id"], date_list
    )
    guesses_by_date: dict = {}
    for r in rows:
        guesses_by_date.setdefault(r["puzzle_date"], []).append(dict(r))

    result = []
    for d in date_list:
        user_guesses = guesses_by_date.get(d, [])
        solved = any(g["is_correct"] for g in user_guesses)
        attempted = len(user_guesses) > 0
        building_id = get_daily_building_id(d)
        building = get_building_by_id(building_id)
        result.append({
            "date": d,
            "building_name": building["name"] if (solved or (attempted and len(user_guesses) >= 6)) else None,
            "solved": solved,
            "attempted": attempted,
            "guesses_used": len(user_guesses),
        })
    return result


@router.get("/past/{date}")
async def get_past_puzzle(date: str, request: Request):
    user = await get_current_user(request)
    building_id = get_daily_building_id(date)
    building = get_building_by_id(building_id)

    pool = get_pool()
    rows = await pool.fetch(
        f"SELECT {_guess_select_cols()} FROM guesses "
        "WHERE user_id = $1 AND puzzle_date = $2 ORDER BY guess_number",
        user["user_id"], date
    )
    guesses = [dict(r) for r in rows]
    is_solved = any(g["is_correct"] for g in guesses)
    is_failed = len(guesses) >= 6 and not is_solved

    result = {
        "puzzle_date": date,
        "guesses": guesses,
        "is_solved": is_solved,
        "is_failed": is_failed,
        "guesses_used": len(guesses),
    }
    if is_solved or is_failed:
        result["building"] = building
    return result
