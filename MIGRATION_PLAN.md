# Silhouettele Migration Guide: Emergent → Self-Hosted

**A complete, opinionated guide to migrating Silhouettele to a free, self-hosted stack.**

*Revised: March 2026*

---

## Table of Contents

1. [Why This Revision Exists](#why-this-revision-exists)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Phase 1: Supabase Project Setup](#phase-1-supabase-project-setup)
5. [Phase 2: Database Schema](#phase-2-database-schema)
6. [Phase 3: Image Migration](#phase-3-image-migration)
7. [Phase 4: Backend Migration](#phase-4-backend-migration)
8. [Phase 5: Frontend Migration](#phase-5-frontend-migration)
9. [Phase 6: Deployment](#phase-6-deployment)
10. [Phase 7: Testing](#phase-7-testing)
11. [Phase 8: MongoDB Data Migration](#phase-8-mongodb-data-migration)
12. [Troubleshooting](#troubleshooting)
13. [Go-Live Checklist](#go-live-checklist)
14. [Cost Summary](#cost-summary)

---

## Why This Revision Exists

The original migration guide has four architectural problems that would cause bugs, performance issues, or unnecessary complexity in production:

| Problem | Original Guide | This Guide |
|---------|---------------|------------|
| **Dual sessions** | Supabase Auth sessions + custom `user_sessions` table + cookies. Two systems to keep in sync. | Supabase Auth only. Backend validates JWT statelessly. No session table. |
| **DB access via HTTP** | `supabase-py` SDK makes HTTP REST calls for every query (~50-150ms each). Leaderboard with 50 user lookups = 5+ seconds. | `asyncpg` connects directly to PostgreSQL. Sub-millisecond queries. SQL JOINs eliminate N+1 patterns. |
| **Client per request** | `async with create_async_client()` in every handler. TCP setup/teardown per request. | Persistent connection pool. Created once at startup. |
| **FK breaks guests** | `guesses.user_id REFERENCES users(user_id)`. Guests use `guest_abc123` which isn't in users table. Every guest guess fails. | No FK on guest-writable tables. |

---

## Architecture Overview

### Current State (Emergent)
```
React (Emergent CDN) → FastAPI (Emergent) → MongoDB (Emergent)
                       OAuth via auth.emergentagent.com
                       Images on Emergent CDN
```

### Target State (Self-Hosted)
```
React (Vercel, free) → FastAPI (Railway, free) → PostgreSQL (Supabase, free)
                        JWT validation only        Auth (Supabase, free)
                                                   Storage (Supabase, free)
```

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND  (Vercel)                      │
│                                                          │
│  @supabase/supabase-js handles:                          │
│    - Google OAuth redirect                               │
│    - Token storage & refresh                             │
│    - Session persistence                                 │
│                                                          │
│  axios sends to backend:                                 │
│    Logged in:  Authorization: Bearer <supabase_jwt>      │
│    Guest:      X-Guest-ID: <localStorage_id>             │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND  (Railway)                       │
│                                                          │
│  FastAPI + uvicorn                                       │
│    auth.py:  jwt.decode(token, secret) → user            │
│              No DB query needed for auth                  │
│    db.py:    asyncpg connection pool                      │
│    routes/:  SQL queries via pool.fetch / pool.execute    │
└────────────────────────┬────────────────────────────────┘
                         │ PostgreSQL protocol (direct)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  SUPABASE  (Free Tier)                    │
│                                                          │
│  PostgreSQL  ← asyncpg direct connection (not REST API)  │
│  Auth        ← Google OAuth, JWT issuance                │
│  Storage     ← 60 silhouette PNGs, public bucket         │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Accounts to Create (All Free)

1. **[Supabase](https://supabase.com)** — Database, Auth, Storage
2. **[Railway](https://railway.app)** — Backend hosting
3. **[Vercel](https://vercel.com)** — Frontend hosting
4. **[Google Cloud Console](https://console.cloud.google.com)** — OAuth credentials

### Local Software

```bash
python --version   # 3.9+
node --version     # 18+
git --version
```

### Time Estimate

| Phase | Hours |
|-------|-------|
| Supabase setup + schema + images | 1-2 |
| Backend migration | 3-4 |
| Frontend migration | 1-2 |
| Deployment | 1 |
| Testing & fixes | 1-2 |
| **Total** | **7-11** |

---

## Phase 1: Supabase Project Setup

### Step 1.1: Create Project

1. Go to [supabase.com](https://supabase.com) → Sign up → **New Project**
2. Fill in:
   - **Name**: `silhouettele`
   - **Database Password**: Generate and save securely
   - **Region**: Choose closest to your users
   - **Plan**: Free
3. Wait 2-3 minutes for initialization

### Step 1.2: Collect Credentials

After project creation, go to **Project Settings** (gear icon):

**From Settings → API:**
```
SUPABASE_URL          = https://abcdefghijklmnop.supabase.co
SUPABASE_ANON_KEY     = eyJhbGciOi...  (public, used by frontend)
```

**From Settings → API → JWT Secret:**
```
SUPABASE_JWT_SECRET   = your-jwt-secret-here  (used by backend to validate tokens)
```

**From Settings → Database → Connection string → URI:**
```
SUPABASE_DB_URL       = postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

Use the **"Transaction" pooler mode** connection string (port 6543), not the direct connection (port 5432). The pooler handles connection limits on the free tier.

Save all four values. You'll need them later.

### Step 1.3: Configure Google OAuth

**In Google Cloud Console:**

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
4. Application type: **Web application**
5. **Authorized redirect URIs**: Add `https://<your-supabase-project>.supabase.co/auth/v1/callback`
6. Copy the **Client ID** and **Client Secret**

**In Supabase Dashboard:**

1. Go to **Authentication → Providers → Google**
2. Toggle **Enable** ON
3. Paste your Google Client ID and Client Secret
4. Save

**Configure redirect URLs:**

1. Go to **Authentication → URL Configuration**
2. **Site URL**: Leave as `http://localhost:3000` for now (update after frontend deploy)
3. **Redirect URLs**: Add:
   - `http://localhost:3000/*`
   - (After deploy, add `https://your-app.vercel.app/*`)

---

## Phase 2: Database Schema

### Step 2.1: Enable Extensions

In Supabase Dashboard → **SQL Editor** → New query:

```sql
create extension if not exists "uuid-ossp";
```

Click **Run**.

### Step 2.2: Create Tables

Run this complete SQL in the SQL Editor:

```sql
-- ═══════════════════════════════════════════════════════
-- SILHOUETTELE DATABASE SCHEMA
-- ═══════════════════════════════════════════════════════

-- Users (registered users only)
create table if not exists public.users (
  user_id text primary key,
  supabase_uid uuid unique,
  email text unique not null,
  name text not null,
  picture text default '',
  username text unique,
  join_date timestamptz default now()
);

-- Guesses (both registered users AND guests write here)
-- NO foreign key on user_id — guests use synthetic IDs like "guest_abc123"
create table if not exists public.guesses (
  guess_id text primary key,
  user_id text not null,
  puzzle_date text not null,
  guess_building_id text not null,
  guess_building_name text not null,
  guess_building_city text not null,
  guess_building_country text not null,
  guess_number integer not null,
  is_correct boolean not null default false,
  direction text default '',
  direction_arrow text default '',
  distance_km integer default 0,
  created_at timestamptz default now(),
  unique(user_id, puzzle_date, guess_number)
);

-- User stats (registered users only)
create table if not exists public.user_stats (
  user_id text primary key references public.users(user_id) on delete cascade,
  puzzles_played integer default 0,
  puzzles_solved integer default 0,
  current_streak integer default 0,
  longest_streak integer default 0,
  total_guesses integer default 0,
  perfect_solves integer default 0,
  last_solved_date text
);

-- Friendships (registered users only)
create table if not exists public.friendships (
  friendship_id text primary key,
  user_id text references public.users(user_id) on delete cascade,
  friend_id text references public.users(user_id) on delete cascade,
  status text check (status in ('pending', 'accepted')) not null default 'pending',
  created_at timestamptz default now(),
  unique(user_id, friend_id),
  check (user_id != friend_id)
);

-- Achievement notification tracking
create table if not exists public.achievement_notifications (
  user_id text primary key references public.users(user_id) on delete cascade,
  notified text[] default '{}'
);

-- Buildings (static reference data, seeded once)
create table if not exists public.buildings (
  building_id text primary key,
  name text not null,
  aliases text default '',
  latitude decimal not null,
  longitude decimal not null,
  city text not null,
  country text not null,
  height_m integer default 0,
  year_built integer default 0,
  fun_fact text default '',
  silhouette_url text default ''
);

-- ═══════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════

create index if not exists idx_guesses_user_date
  on public.guesses(user_id, puzzle_date);

create index if not exists idx_guesses_date
  on public.guesses(puzzle_date);

create index if not exists idx_guesses_date_correct
  on public.guesses(puzzle_date, is_correct);

create index if not exists idx_friendships_user_status
  on public.friendships(user_id, status);

create index if not exists idx_friendships_friend_status
  on public.friendships(friend_id, status);

create index if not exists idx_users_supabase_uid
  on public.users(supabase_uid);

create index if not exists idx_users_email
  on public.users(email);

create index if not exists idx_users_username
  on public.users(username);

-- ═══════════════════════════════════════════════════════
-- DISABLE ROW LEVEL SECURITY
-- The backend is the sole DB accessor. All auth is handled
-- at the application layer. RLS adds overhead with no benefit.
-- ═══════════════════════════════════════════════════════

alter table public.users disable row level security;
alter table public.guesses disable row level security;
alter table public.user_stats disable row level security;
alter table public.friendships disable row level security;
alter table public.achievement_notifications disable row level security;
alter table public.buildings disable row level security;
```

Click **Run**. All tables and indexes will be created.

---

## Phase 3: Image Migration

### Step 3.1: Download Images from Emergent

Create `scripts/download_images.py`:

```python
import requests
import os

os.makedirs("silhouette_images", exist_ok=True)

# Paste the full SILHOUETTE_URLS dict from backend/data/buildings.py
SILHOUETTE_URLS = {
    "b001": "https://static.prod-images.emergentagent.com/jobs/72a862c5-cbd4-41a8-99f9-4532f3520664/images/46046c795ce52169949ca3259084e0f989b680cc7febf5562b043bc73c509bf5.png",
    "b002": "https://static.prod-images.emergentagent.com/jobs/72a862c5-cbd4-41a8-99f9-4532f3520664/images/798e68d9985077597091a02ea61691bbf63b87dbf8ba33e9e2ae80c2b5039609.png",
    # ... all 60 entries from backend/data/buildings.py ...
    "b060": "https://static.prod-images.emergentagent.com/jobs/72a862c5-cbd4-41a8-99f9-4532f3520664/images/a4c33611069b8f22673abb06a335adfbbdb875a9c8e3bbb8c461923c8a0b0d8d.png",
}

for bid, url in SILHOUETTE_URLS.items():
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(f"silhouette_images/{bid}.png", "wb") as f:
            f.write(r.content)
        print(f"  {bid}.png")
    except Exception as e:
        print(f"  FAILED {bid}: {e}")

print(f"\nDone. {len(SILHOUETTE_URLS)} images.")
```

Run:
```bash
pip install requests
python scripts/download_images.py
```

### Step 3.2: Upload to Supabase Storage

1. In Supabase Dashboard → **Storage** → **New bucket**
2. Name: `silhouettes`
3. **Public bucket**: ON
4. Allowed MIME types: `image/png`
5. Click **Create bucket**
6. Open the `silhouettes` bucket → drag & drop all 60 PNGs from `silhouette_images/`

### Step 3.3: Generate New URLs

Your images are now at:
```
https://<your-project-ref>.supabase.co/storage/v1/object/public/silhouettes/b001.png
https://<your-project-ref>.supabase.co/storage/v1/object/public/silhouettes/b002.png
...
```

Create `scripts/generate_urls.py`:

```python
PROJECT_REF = "your-project-ref-here"  # from your Supabase URL

base = f"https://{PROJECT_REF}.supabase.co/storage/v1/object/public/silhouettes"

print("SILHOUETTE_URLS = {")
for i in range(1, 61):
    bid = f"b{i:03d}"
    print(f'    "{bid}": "{base}/{bid}.png",')
print("}")
```

Run it, copy the output, and replace the `SILHOUETTE_URLS` dict in `backend/data/buildings.py`.

---

## Phase 4: Backend Migration

### File Structure (After Migration)

```
backend/
├── server.py              # App setup, middleware, lifecycle
├── db.py                  # asyncpg connection pool
├── auth.py                # JWT validation + guest fallback
├── utils.py               # Haversine, daily building (UNCHANGED)
├── models.py              # Pydantic models (UNCHANGED)
├── data/
│   └── buildings.py       # BUILDINGS + SILHOUETTE_URLS (URLs updated)
├── routes/
│   ├── auth.py            # register, me, logout, profile
│   ├── buildings.py       # search, list (UNCHANGED — uses in-memory data)
│   ├── puzzle.py          # today, guess, share, calendar, past, seed
│   ├── stats.py           # my stats
│   ├── friends.py         # friend system
│   ├── leaderboard.py     # overall + friends leaderboard
│   ├── achievements.py    # badges
│   └── challenges.py      # weekly/monthly challenges
├── requirements.txt
└── .env
```

### Step 4.1: requirements.txt

```
fastapi
uvicorn[standard]
python-dotenv
pydantic
httpx
asyncpg
python-jose[cryptography]
```

Install:
```bash
cd backend
pip install -r requirements.txt
```

### Step 4.2: .env

```env
SUPABASE_DB_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-settings
CORS_ORIGINS=http://localhost:3000
```

### Step 4.3: db.py

```python
import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

DATABASE_URL = os.environ['SUPABASE_DB_URL']

_pool: asyncpg.Pool = None


async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


async def close_db():
    global _pool
    if _pool:
        await _pool.close()


def get_pool() -> asyncpg.Pool:
    return _pool
```

### Step 4.4: auth.py

```python
from fastapi import HTTPException, Request
from jose import jwt, JWTError
from db import get_pool
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

SUPABASE_JWT_SECRET = os.environ['SUPABASE_JWT_SECRET']


async def get_current_user(request: Request) -> dict:
    """Validate Supabase JWT and return app user. No session table needed."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(
            token, SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    supabase_uid = payload.get("sub")
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
    """Returns authenticated user or guest. Used by puzzle endpoints."""
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
```

### Step 4.5: models.py (UNCHANGED)

```python
from pydantic import BaseModel
from typing import Optional


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    username: Optional[str] = None
    join_date: Optional[str] = None


class GuessRequest(BaseModel):
    building_id: str


class UsernameUpdate(BaseModel):
    username: str


class FriendRequest(BaseModel):
    friend_user_id: str
```

### Step 4.6: utils.py (UNCHANGED)

Copy as-is from the current codebase. No database dependency.

```python
import math
import hashlib
from datetime import datetime, timezone
from data.buildings import BUILDINGS


def to_radians(degrees):
    return degrees * math.pi / 180


def to_degrees(radians):
    return radians * 180 / math.pi


def calculate_direction_distance(guess_lat, guess_lng, correct_lat, correct_lng):
    phi1 = to_radians(guess_lat)
    phi2 = to_radians(correct_lat)
    delta_lambda = to_radians(correct_lng - guess_lng)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    theta = math.atan2(y, x)
    bearing = (to_degrees(theta) + 360) % 360
    points = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
              "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    index = round(bearing / 22.5) % 16
    direction = points[index]
    R = 6371
    delta_phi = to_radians(correct_lat - guess_lat)
    delta_lambda2 = to_radians(correct_lng - guess_lng)
    a = (math.sin(delta_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda2 / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = round(R * c)
    return direction, distance


def get_daily_building_id(date_str: str) -> str:
    seed = hashlib.md5(f"silhouettele-{date_str}".encode()).hexdigest()
    index = int(seed, 16) % len(BUILDINGS)
    return BUILDINGS[index]["building_id"]


def get_today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_building_by_id(building_id: str):
    for b in BUILDINGS:
        if b["building_id"] == building_id:
            return b
    return None


def get_direction_arrow(direction: str) -> str:
    arrows = {
        "N": "\u2191", "NNE": "\u2197", "NE": "\u2197", "ENE": "\u2197",
        "E": "\u2192", "ESE": "\u2198", "SE": "\u2198", "SSE": "\u2198",
        "S": "\u2193", "SSW": "\u2199", "SW": "\u2199", "WSW": "\u2199",
        "W": "\u2190", "WNW": "\u2196", "NW": "\u2196", "NNW": "\u2196"
    }
    return arrows.get(direction, "")
```

### Step 4.7: data/buildings.py

**UNCHANGED** except for `SILHOUETTE_URLS` values. Replace the Emergent CDN URLs with your Supabase Storage URLs from Phase 3, Step 3.3. The `BUILDINGS` list stays identical.

### Step 4.8: routes/auth.py

```python
from fastapi import APIRouter, HTTPException, Request
from jose import jwt, JWTError
from db import get_pool
from auth import get_current_user
from models import UsernameUpdate
import uuid
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env')

SUPABASE_JWT_SECRET = os.environ['SUPABASE_JWT_SECRET']

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register_user(request: Request):
    """Called by frontend after Supabase OAuth login.
    Creates an app user record if one doesn't exist for this Supabase user.
    Returns the app user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(
            token, SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    supabase_uid = payload.get("sub")
    email = payload.get("email", "")
    metadata = payload.get("user_metadata", {})
    name = metadata.get("full_name", "") or metadata.get("name", "") or email.split("@")[0]
    picture = metadata.get("avatar_url", "") or metadata.get("picture", "")

    pool = get_pool()

    # Check if user already exists
    existing = await pool.fetchrow(
        "SELECT user_id, email, name, picture, username, "
        "to_char(join_date, 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') as join_date "
        "FROM users WHERE supabase_uid = $1",
        supabase_uid
    )
    if existing:
        # Update name/picture in case they changed on Google's side
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

    # Create new user
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
    """Backend logout is a no-op. Frontend handles Supabase signout."""
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
```

### Step 4.9: routes/buildings.py (UNCHANGED)

```python
from fastapi import APIRouter
from data.buildings import BUILDINGS

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("/search")
async def search_buildings(q: str = ""):
    if not q or len(q) < 2:
        return []
    q_lower = q.lower()
    results = []
    for b in BUILDINGS:
        if (q_lower in b["name"].lower()
                or q_lower in b.get("aliases", "").lower()
                or q_lower in b["city"].lower()
                or q_lower in b["country"].lower()):
            results.append({
                "building_id": b["building_id"],
                "name": b["name"],
                "city": b["city"],
                "country": b["country"]
            })
    return results[:10]


@router.get("")
async def list_buildings():
    return [{"building_id": b["building_id"], "name": b["name"],
             "city": b["city"], "country": b["country"]} for b in BUILDINGS]
```

### Step 4.10: routes/puzzle.py

```python
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


DIRECTION_EMOJIS = {
    "N": "\u2191", "NNE": "\u2197", "NE": "\u2197", "ENE": "\u2197",
    "E": "\u2192", "ESE": "\u2198", "SE": "\u2198", "SSE": "\u2198",
    "S": "\u2193", "SSW": "\u2199", "SW": "\u2199", "WSW": "\u2199",
    "W": "\u2190", "WNW": "\u2196", "NW": "\u2196", "NNW": "\u2196"
}


async def _update_user_stats(pool, user_id: str, guess_number: int, puzzle_date: str):
    row = await pool.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)

    if not row:
        await pool.execute(
            """INSERT INTO user_stats
               (user_id, puzzles_played, puzzles_solved, total_guesses, perfect_solves,
                current_streak, longest_streak, last_solved_date)
               VALUES ($1, 0, 0, 0, 0, 0, 0, NULL)""",
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
    row = await pool.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)

    if not row:
        await pool.execute(
            """INSERT INTO user_stats
               (user_id, puzzles_played, puzzles_solved, total_guesses, perfect_solves,
                current_streak, longest_streak, last_solved_date)
               VALUES ($1, 0, 0, 0, 0, 0, 0, NULL)""",
            user_id
        )
        row = await pool.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    last_date = row["last_solved_date"]
    reset_streak = last_date != yesterday and last_date != puzzle_date

    if reset_streak:
        await pool.execute(
            """UPDATE user_stats SET
               puzzles_played = puzzles_played + 1,
               total_guesses = total_guesses + 6,
               current_streak = 0
               WHERE user_id = $1""",
            user_id
        )
    else:
        await pool.execute(
            """UPDATE user_stats SET
               puzzles_played = puzzles_played + 1,
               total_guesses = total_guesses + 6
               WHERE user_id = $1""",
            user_id
        )


@router.get("/today")
async def get_today_puzzle(request: Request):
    user = await get_user_or_guest(request)
    today = get_today_str()
    building_id = get_daily_building_id(today)
    building = get_building_by_id(building_id)

    pool = get_pool()
    rows = await pool.fetch(
        """SELECT guess_id, user_id, puzzle_date, guess_building_id, guess_building_name,
           guess_building_city, guess_building_country, guess_number, is_correct,
           direction, direction_arrow, distance_km
           FROM guesses WHERE user_id = $1 AND puzzle_date = $2
           ORDER BY guess_number""",
        user["user_id"], today
    )
    guesses = [dict(r) for r in rows]

    is_solved = any(g["is_correct"] for g in guesses)
    is_failed = len(guesses) >= 6 and not is_solved

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

    pool = get_pool()
    rows = await pool.fetch(
        """SELECT guess_building_id, is_correct FROM guesses
           WHERE user_id = $1 AND puzzle_date = $2""",
        user["user_id"], today
    )
    existing = [dict(r) for r in rows]

    if any(g["is_correct"] for g in existing):
        raise HTTPException(status_code=400, detail="Already solved today's puzzle")
    if len(existing) >= 6:
        raise HTTPException(status_code=400, detail="No guesses left")
    if body.building_id in {g["guess_building_id"] for g in existing}:
        raise HTTPException(status_code=400, detail="You already guessed this building today")

    guessed_building = get_building_by_id(body.building_id)
    if not guessed_building:
        raise HTTPException(status_code=400, detail="Building not in database")

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

    await pool.execute(
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

    # Update stats for registered users only
    if not user.get("is_guest"):
        if is_correct:
            await _update_user_stats(pool, user["user_id"], guess_number, today)
        elif guess_number >= 6:
            await _update_user_stats_failed(pool, user["user_id"], today)

    # Fetch all guesses for response
    all_rows = await pool.fetch(
        """SELECT guess_id, user_id, puzzle_date, guess_building_id, guess_building_name,
           guess_building_city, guess_building_country, guess_number, is_correct,
           direction, direction_arrow, distance_km
           FROM guesses WHERE user_id = $1 AND puzzle_date = $2
           ORDER BY guess_number""",
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
        """SELECT is_correct, direction, distance_km FROM guesses
           WHERE user_id = $1 AND puzzle_date = $2 ORDER BY guess_number""",
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
            arrow = DIRECTION_EMOJIS.get(g.get("direction", ""), "?")
            dist = g.get("distance_km", 0)
            if dist < 500:    bar = "\u2588\u2588\u2588\u2588"
            elif dist < 2000: bar = "\u2588\u2588\u2588\u2591"
            elif dist < 5000: bar = "\u2588\u2588\u2591\u2591"
            else:             bar = "\u2588\u2591\u2591\u2591"
            lines.append(f"{bar} {arrow} {dist:,} km")

    lines.extend(["", "Play at silhouettele.com"])
    return {"share_text": "\n".join(lines), "is_solved": is_solved, "score": score}


@router.get("/calendar")
async def get_puzzle_calendar(request: Request):
    user = await get_current_user(request)
    pool = get_pool()

    dates = []
    for i in range(30):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        building_id = get_daily_building_id(d)
        building = get_building_by_id(building_id)

        rows = await pool.fetch(
            "SELECT is_correct FROM guesses WHERE user_id = $1 AND puzzle_date = $2",
            user["user_id"], d
        )
        user_guesses = [dict(r) for r in rows]
        solved = any(g["is_correct"] for g in user_guesses)
        attempted = len(user_guesses) > 0

        dates.append({
            "date": d,
            "building_name": building["name"] if (solved or (attempted and len(user_guesses) >= 6)) else None,
            "solved": solved,
            "attempted": attempted,
            "guesses_used": len(user_guesses),
        })
    return dates


@router.get("/past/{date}")
async def get_past_puzzle(date: str, request: Request):
    user = await get_current_user(request)
    building_id = get_daily_building_id(date)
    building = get_building_by_id(building_id)

    pool = get_pool()
    rows = await pool.fetch(
        """SELECT guess_id, user_id, puzzle_date, guess_building_id, guess_building_name,
           guess_building_city, guess_building_country, guess_number, is_correct,
           direction, direction_arrow, distance_km
           FROM guesses WHERE user_id = $1 AND puzzle_date = $2
           ORDER BY guess_number""",
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


@router.post("/seed")
async def seed_buildings():
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM buildings")
    if count > 0:
        return {"message": f"Already seeded ({count} buildings)"}

    for b in BUILDINGS:
        await pool.execute(
            """INSERT INTO buildings
               (building_id, name, aliases, latitude, longitude, city, country,
                height_m, year_built, fun_fact, silhouette_url)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
               ON CONFLICT (building_id) DO NOTHING""",
            b["building_id"], b["name"], b.get("aliases", ""),
            b["latitude"], b["longitude"], b["city"], b["country"],
            b.get("height_m", 0), b.get("year_built", 0),
            b.get("fun_fact", ""),
            SILHOUETTE_URLS.get(b["building_id"], "")
        )
    return {"message": f"Seeded {len(BUILDINGS)} buildings"}
```

### Step 4.11: routes/stats.py

```python
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
```

### Step 4.12: routes/friends.py

```python
from fastapi import APIRouter, HTTPException, Request
from db import get_pool
from models import FriendRequest
from auth import get_current_user
import uuid
from datetime import datetime, timezone

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
           AND (username ILIKE $2 OR name ILIKE $2 OR email ILIKE $2)
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
```

### Step 4.13: routes/leaderboard.py

Note how SQL JOINs eliminate the N+1 query problem from the original code:

```python
from fastapi import APIRouter, Request
from db import get_pool
from auth import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/overall")
async def get_overall_leaderboard(metric: str = "puzzles_solved", request: Request = None):
    user = await get_current_user(request)
    valid = {"puzzles_solved", "current_streak", "longest_streak", "perfect_solves"}
    if metric not in valid:
        metric = "puzzles_solved"

    pool = get_pool()
    # Single query with JOIN — no N+1 problem
    rows = await pool.fetch(
        f"""SELECT us.*, u.user_id, u.username, u.name, u.picture
            FROM user_stats us
            JOIN users u ON us.user_id = u.user_id
            ORDER BY us.{metric} DESC
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
    valid = {"puzzles_solved", "current_streak", "longest_streak", "perfect_solves"}
    if metric not in valid:
        metric = "puzzles_solved"

    pool = get_pool()

    # Get friend IDs (including self)
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
            ORDER BY us.{metric} DESC""",
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
```

### Step 4.14: routes/achievements.py

```python
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


def _check_achievements(stats: dict) -> list:
    earned = []
    for a in ACHIEVEMENTS:
        field, op, val = a["condition"].split(" ")
        if op == ">=" and (stats.get(field, 0) or 0) >= int(val):
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

    # Get previously notified
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

    # Mark new badges as notified
    if new_badges:
        all_notified = list(set(notified_ids + new_badges))
        await pool.execute(
            """INSERT INTO achievement_notifications (user_id, notified)
               VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET notified = $2""",
            user["user_id"], all_notified
        )

    return {"achievements": result, "earned_count": len(earned_ids), "total_count": len(ACHIEVEMENTS)}
```

### Step 4.15: routes/challenges.py

```python
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

    # Weekly stats — single query
    week_rows = await pool.fetch(
        """SELECT puzzle_date, is_correct FROM guesses
           WHERE user_id = $1 AND puzzle_date = ANY($2)""",
        user["user_id"], week_dates
    )
    week_solved = {r["puzzle_date"] for r in week_rows if r["is_correct"]}
    week_days = len({r["puzzle_date"] for r in week_rows})
    week_total = len(week_rows)

    # Monthly stats — single query
    month_rows = await pool.fetch(
        """SELECT puzzle_date, is_correct FROM guesses
           WHERE user_id = $1 AND puzzle_date = ANY($2)""",
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

    # Single aggregation query with JOIN — replaces N+1 pattern
    rows = await pool.fetch(
        """SELECT g.user_id, u.username, u.name, u.picture,
                  COUNT(DISTINCT CASE WHEN g.is_correct THEN g.puzzle_date END) as solved,
                  COUNT(*) as total_guesses
           FROM guesses g
           LEFT JOIN users u ON g.user_id = u.user_id
           WHERE g.puzzle_date = ANY($1)
           AND g.user_id NOT LIKE 'guest_%%'
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
```

### Step 4.16: server.py

```python
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from db import init_db, close_db
import os
import logging

from routes.auth import router as auth_router
from routes.buildings import router as buildings_router
from routes.puzzle import router as puzzle_router
from routes.stats import router as stats_router
from routes.friends import router as friends_router
from routes.leaderboard import router as leaderboard_router
from routes.achievements import router as achievements_router
from routes.challenges import router as challenges_router

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI()
api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(buildings_router)
api_router.include_router(puzzle_router)
api_router.include_router(stats_router)
api_router.include_router(friends_router)
api_router.include_router(leaderboard_router)
api_router.include_router(achievements_router)
api_router.include_router(challenges_router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    await close_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Phase 5: Frontend Migration

### Step 5.1: Install Supabase JS

```bash
cd frontend
yarn add @supabase/supabase-js
```

### Step 5.2: Remove Emergent Dependencies

```bash
# Remove Emergent package from package.json
yarn remove @emergentbase/visual-edits
```

Clean up `craco.config.js` — remove the `withVisualEdits` wrapper if present.

### Step 5.3: .env

```env
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-anon-public-key
```

### Step 5.4: Create Supabase Client

**New file: `frontend/src/lib/supabase.js`**

```javascript
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL,
  process.env.REACT_APP_SUPABASE_ANON_KEY
);
```

### Step 5.5: Update API Client (`src/api.js`)

Replace cookie-based auth with JWT-based auth:

```javascript
import axios from "axios";
import { supabase } from "./lib/supabase";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getGuestId = () => {
  let guestId = localStorage.getItem("silhouettele_guest_id");
  if (!guestId) {
    guestId = "g_" + Math.random().toString(36).substring(2, 14) + Date.now().toString(36);
    localStorage.setItem("silhouettele_guest_id", guestId);
  }
  return guestId;
};

const api = axios.create({ baseURL: API });

// Attach Supabase JWT or guest ID to every request
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers["Authorization"] = `Bearer ${session.access_token}`;
  } else {
    config.headers["X-Guest-ID"] = getGuestId();
  }
  return config;
});

export default api;
```

### Step 5.6: Update AuthContext (`src/authContext.js`)

```javascript
import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "./lib/supabase";
import api from "./api";

const AuthContext = createContext(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Register/fetch app user from backend after Supabase auth
  const syncUser = useCallback(async () => {
    try {
      const res = await api.post("/auth/register");
      setUser(res.data);
    } catch (err) {
      console.error("Failed to sync user:", err);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    // Check initial session
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        await syncUser();
      }
      setLoading(false);
    };
    init();

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        if (event === "SIGNED_IN" && session) {
          await syncUser();
        } else if (event === "SIGNED_OUT") {
          setUser(null);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [syncUser]);

  const login = (userData) => setUser(userData);

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
    navigate("/login", { replace: true });
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
```

### Step 5.7: Update LoginPage

Replace the Emergent OAuth redirect with Supabase OAuth:

```javascript
// In your login handler:
const handleGoogleLogin = async () => {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin,
    },
  });
  if (error) console.error("Login error:", error.message);
};
```

The Supabase JS client handles the entire OAuth redirect flow. No backend endpoint needed for login initiation.

### Step 5.8: Simplify AuthCallback

After Supabase OAuth, the user is redirected back to your app with tokens in the URL. The Supabase JS client automatically picks them up. If you have a dedicated `/auth/callback` route, simplify it:

```javascript
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    // Supabase JS client handles token exchange automatically.
    // Just wait a moment and redirect to home.
    const timer = setTimeout(() => navigate("/", { replace: true }), 1500);
    return () => clearTimeout(timer);
  }, [navigate]);

  return <div className="flex items-center justify-center h-screen">Signing in...</div>;
}
```

Or remove the callback page entirely and set `redirectTo: window.location.origin` so the user returns to the homepage where `onAuthStateChange` handles the rest.

---

## Phase 6: Deployment

### Step 6.1: Push to GitHub

```bash
git add .
git commit -m "Migrate to Supabase + asyncpg"
git push origin main
```

Make sure `.env` files are in `.gitignore`.

### Step 6.2: Deploy Backend to Railway

1. Go to [railway.app](https://railway.app) → Sign up with GitHub
2. **New Project** → **Deploy from GitHub Repo** → Select your repo
3. Railway settings:
   - **Root Directory**: `backend`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. **Variables** tab — add:
   ```
   SUPABASE_DB_URL=postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres
   SUPABASE_JWT_SECRET=your-jwt-secret
   CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
   ```
5. **Settings → Networking** → Enable **Public Networking**
6. Copy your Railway URL (e.g. `https://silhouettele-backend.up.railway.app`)

### Step 6.3: Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → Sign up with GitHub
2. **New Project** → Import your repo
3. Settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Create React App
   - **Build Command**: `yarn build`
   - **Output Directory**: `build`
4. **Environment Variables**:
   ```
   REACT_APP_BACKEND_URL=https://your-railway-url.up.railway.app
   REACT_APP_SUPABASE_URL=https://your-project.supabase.co
   REACT_APP_SUPABASE_ANON_KEY=your-anon-public-key
   ```
5. Deploy. Your app will be at `https://your-app.vercel.app`

### Step 6.4: Post-Deploy Configuration

1. **Supabase Auth → URL Configuration**:
   - Update **Site URL** to `https://your-app.vercel.app`
   - Add `https://your-app.vercel.app/*` to **Redirect URLs**

2. **Railway → Variables**:
   - Update `CORS_ORIGINS` to include your Vercel URL

3. **Google Cloud Console → OAuth credentials**:
   - Verify redirect URI includes `https://<your-supabase-project>.supabase.co/auth/v1/callback`

---

## Phase 7: Testing

### Test Flows

1. **Guest Play** (no login required):
   - Open app → should see puzzle immediately
   - Search for a building → make a guess
   - Verify guess appears in the 6-slot grid
   - Check Supabase → `guesses` table should have a row with `user_id = "guest_..."`

2. **Google Login**:
   - Click "Sign In" → "Continue with Google"
   - Should redirect to Google → back to app
   - Check Supabase → `users` table should have your record

3. **Authenticated Play**:
   - As logged-in user, make guesses
   - Check `user_stats` table updates after solving

4. **Logout + Re-login**:
   - Logout, login again
   - Previous guesses should still be visible

5. **API Smoke Test**:
   ```bash
   # Guest puzzle fetch
   curl -H "X-Guest-ID: test123" https://your-backend.up.railway.app/api/puzzle/today

   # Building search
   curl https://your-backend.up.railway.app/api/buildings/search?q=eiffel

   # Health check
   curl https://your-backend.up.railway.app/health
   ```

---

## Phase 8: MongoDB Data Migration

Skip this if you have no existing user data worth keeping.

### Migration Script

```python
"""
Migrate data from MongoDB to Supabase PostgreSQL.
Run locally with both databases accessible.
"""
import asyncio
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb://localhost:27017"
MONGO_DB = "test_database"
PG_URL = "postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres"


async def migrate():
    # Connect to both databases
    mongo = AsyncIOMotorClient(MONGO_URL)
    mdb = mongo[MONGO_DB]
    pool = await asyncpg.create_pool(PG_URL)

    # Migrate users (supabase_uid will be NULL — backfilled on next login)
    users = await mdb.users.find({}, {"_id": 0}).to_list(10000)
    for u in users:
        await pool.execute(
            """INSERT INTO users (user_id, email, name, picture, username, join_date)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT (user_id) DO NOTHING""",
            u["user_id"], u["email"], u["name"], u.get("picture", ""),
            u.get("username"), u.get("join_date")
        )
    print(f"Migrated {len(users)} users")

    # Migrate guesses
    guesses = await mdb.guesses.find({}, {"_id": 0}).to_list(100000)
    for g in guesses:
        await pool.execute(
            """INSERT INTO guesses
               (guess_id, user_id, puzzle_date, guess_building_id, guess_building_name,
                guess_building_city, guess_building_country, guess_number, is_correct,
                direction, direction_arrow, distance_km)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
               ON CONFLICT DO NOTHING""",
            g.get("guess_id", ""), g["user_id"], g["puzzle_date"],
            g["guess_building_id"], g["guess_building_name"],
            g.get("guess_building_city", ""), g.get("guess_building_country", ""),
            g["guess_number"], g["is_correct"],
            g.get("direction", ""), g.get("direction_arrow", ""),
            g.get("distance_km", 0)
        )
    print(f"Migrated {len(guesses)} guesses")

    # Migrate user_stats
    stats = await mdb.user_stats.find({}, {"_id": 0}).to_list(10000)
    for s in stats:
        await pool.execute(
            """INSERT INTO user_stats
               (user_id, puzzles_played, puzzles_solved, current_streak,
                longest_streak, total_guesses, perfect_solves, last_solved_date)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
               ON CONFLICT (user_id) DO NOTHING""",
            s["user_id"], s.get("puzzles_played", 0), s.get("puzzles_solved", 0),
            s.get("current_streak", 0), s.get("longest_streak", 0),
            s.get("total_guesses", 0), s.get("perfect_solves", 0),
            s.get("last_solved_date")
        )
    print(f"Migrated {len(stats)} user stats")

    # Migrate friendships
    friends = await mdb.friendships.find({}, {"_id": 0}).to_list(10000)
    for f in friends:
        await pool.execute(
            """INSERT INTO friendships (friendship_id, user_id, friend_id, status)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT DO NOTHING""",
            f.get("friendship_id", ""), f["user_id"], f["friend_id"], f["status"]
        )
    print(f"Migrated {len(friends)} friendships")

    await pool.close()
    mongo.close()
    print("\nMigration complete.")


asyncio.run(migrate())
```

**Note on `supabase_uid`**: Migrated users will have `supabase_uid = NULL`. When they log in with Google via Supabase for the first time, the `/auth/register` endpoint should be updated to check by email first:

```python
# In routes/auth.py register endpoint, add before the supabase_uid lookup:
existing_by_email = await pool.fetchrow(
    "SELECT * FROM users WHERE email = $1", email
)
if existing_by_email and not existing_by_email["supabase_uid"]:
    # Backfill supabase_uid for migrated user
    await pool.execute(
        "UPDATE users SET supabase_uid = $1, name = $2, picture = $3 WHERE email = $4",
        supabase_uid, name, picture, email
    )
    return dict(await pool.fetchrow("SELECT * FROM users WHERE email = $1", email))
```

---

## Troubleshooting

### CORS Errors
```
Access to fetch blocked by CORS policy
```
**Fix**: Ensure `CORS_ORIGINS` in Railway includes your exact Vercel URL (no trailing slash).

### "User not registered" After Login
The Supabase JWT is valid but no matching user exists in the `users` table.
**Fix**: Ensure the frontend calls `POST /api/auth/register` after Supabase login (the `onAuthStateChange` handler should do this).

### Guest Guesses Failing
**Fix**: Verify there's no foreign key on `guesses.user_id`. Run:
```sql
SELECT conname FROM pg_constraint WHERE conrelid = 'guesses'::regclass AND contype = 'f';
```
If any FK references `users`, drop it:
```sql
ALTER TABLE guesses DROP CONSTRAINT <constraint_name>;
```

### asyncpg Connection Errors
```
asyncpg.exceptions.TooManyConnectionsError
```
**Fix**: Use the Supabase connection pooler URL (port 6543), not the direct connection (port 5432). Reduce pool size if needed: `min_size=1, max_size=5`.

### JWT Validation Fails
```
JWTError: Invalid token
```
**Fix**: Ensure `SUPABASE_JWT_SECRET` matches exactly what's in Supabase Settings → API → JWT Secret. No trailing whitespace.

### Images Not Loading (403)
**Fix**: Ensure the `silhouettes` bucket is set to **Public**. Test URL directly in browser:
```
https://<project>.supabase.co/storage/v1/object/public/silhouettes/b001.png
```

### Railway Boot Timeout
**Fix**: Start command must use `$PORT`:
```
uvicorn server:app --host 0.0.0.0 --port $PORT
```

---

## Go-Live Checklist

### Supabase
- [ ] Project created
- [ ] Schema SQL executed (all tables + indexes)
- [ ] RLS disabled on all tables
- [ ] Google OAuth provider enabled
- [ ] Site URL set to production frontend URL
- [ ] Redirect URLs configured
- [ ] Storage bucket `silhouettes` created and public
- [ ] 60 images uploaded
- [ ] JWT Secret copied

### Backend (Railway)
- [ ] Deployed successfully
- [ ] `SUPABASE_DB_URL` set
- [ ] `SUPABASE_JWT_SECRET` set
- [ ] `CORS_ORIGINS` includes frontend URL
- [ ] Start command uses `$PORT`
- [ ] `/health` endpoint responds
- [ ] Guest puzzle fetch works: `curl -H "X-Guest-ID: test" <url>/api/puzzle/today`

### Frontend (Vercel)
- [ ] Deployed successfully
- [ ] `REACT_APP_BACKEND_URL` points to Railway
- [ ] `REACT_APP_SUPABASE_URL` set
- [ ] `REACT_APP_SUPABASE_ANON_KEY` set
- [ ] No Emergent dependencies in package.json
- [ ] No console errors

### Functional
- [ ] Guest can play without logging in
- [ ] Google login works end-to-end
- [ ] Guesses persist and show in grid
- [ ] Stats update after solving
- [ ] Leaderboard loads
- [ ] Share text generates correctly
- [ ] Images load (no broken silhouettes)
- [ ] Mobile responsive

### Security
- [ ] `.env` files in `.gitignore`
- [ ] No secrets in committed code
- [ ] `SUPABASE_SERVICE_ROLE_KEY` NOT used anywhere (not needed)
- [ ] Only `SUPABASE_ANON_KEY` exposed to frontend (this is safe — it's designed to be public)

---

## Cost Summary

| Service | Free Tier Limits | Silhouettele Usage | Monthly Cost |
|---------|-----------------|-------------------|-------------|
| Supabase | 500MB DB, 1GB storage, 50k MAU | ~10MB, ~100MB, <1k users | $0 |
| Railway | $5/month credit | ~$2-3 for small FastAPI | $0 |
| Vercel | 100GB bandwidth | <1GB | $0 |
| Google OAuth | Unlimited | Unlimited | $0 |
| **Total** | | | **$0** |

If you grow beyond free tiers: Supabase Pro ($25/mo), Railway Pro ($5/mo), Vercel Pro ($20/mo) = $50/mo for thousands of active users.

---

## What Stays the Same

These files are copied as-is with zero changes:
- `backend/utils.py` — Pure math functions, no DB dependency
- `backend/models.py` — Pydantic models
- `backend/data/buildings.py` — Only SILHOUETTE_URLS values change
- `backend/routes/buildings.py` — Uses in-memory data, no DB
- All frontend pages and components (except auth-related ones)
- All frontend styling (CSS, Tailwind config)
- Guest mode UX and localStorage stats

## What Changes

| File | Change |
|------|--------|
| `backend/db.py` | Motor/MongoDB → asyncpg/PostgreSQL |
| `backend/auth.py` | Cookie+session lookup → JWT decode |
| `backend/routes/auth.py` | Emergent OAuth → register from JWT |
| `backend/routes/puzzle.py` | MongoDB queries → SQL |
| `backend/routes/stats.py` | MongoDB queries → SQL |
| `backend/routes/friends.py` | MongoDB queries → SQL + JOINs |
| `backend/routes/leaderboard.py` | N+1 MongoDB → single SQL JOIN |
| `backend/routes/achievements.py` | MongoDB queries → SQL |
| `backend/routes/challenges.py` | MongoDB aggregation → SQL GROUP BY |
| `backend/server.py` | Add startup/shutdown lifecycle |
| `frontend/src/api.js` | Cookies → JWT Authorization header |
| `frontend/src/authContext.js` | Emergent auth → Supabase auth |
| `frontend/src/pages/LoginPage.jsx` | Emergent redirect → supabase.auth.signInWithOAuth |
| `frontend/.env` | Add Supabase URL + anon key |
