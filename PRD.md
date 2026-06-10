# Silhouettele — Product Requirements & Project Overview

> A daily puzzle game where players guess a famous building from its silhouette in 6 tries.
> **Live:** https://www.silhouettele.cc · **API:** https://api.silhouettele.cc

---

## 1. Overview

Silhouettele is a Wordle-style daily game. Each day a famous building's silhouette is shown,
and the player has **6 guesses** to identify it. Every incorrect guess returns a **direction arrow**
(toward the correct building) and the **distance in km**, helping the player triangulate the answer.

- One shared **daily puzzle** for all players, selected automatically by date.
- Play instantly as a **guest** (progress stored locally) or sign in for persistent stats, friends and leaderboards.
- Social layer: friends, friend leaderboards, achievements, and weekly/monthly challenges.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, React Router 7, TailwindCSS, shadcn/ui, framer-motion, CRACO |
| Backend | FastAPI (Python 3.11), asyncpg |
| Database | Supabase **PostgreSQL** (RLS enabled, no client policies; backend connects via the direct Postgres connection — see §5.1) |
| Auth | Supabase Auth — **Google OAuth** + email/password; **guest mode** via `X-Guest-ID` header |
| Storage | Supabase Storage — 60 silhouette PNGs in public `silhouettes` bucket |
| Hosting | **Frontend → Vercel**, **Backend → Railway**, DB/Auth/Storage → Supabase |
| Domain | `silhouettele.cc` (Namecheap) → www on Vercel, `api.` on Railway |

> Migration note: the app was fully migrated off MongoDB/Emergent services to a self-hosted
> Supabase stack (Postgres + Auth + Storage). No MongoDB/`motor` code remains.

---

## 3. Architecture

```
silhouettele.cc (Vercel, React)
        │  axios → injects Supabase JWT  OR  X-Guest-ID header
        ▼
api.silhouettele.cc (Railway, FastAPI)
        │  asyncpg pool (statement_cache_size=0 for pgbouncer)
        ▼
Supabase  ── PostgreSQL (RLS)
          ── Auth  (JWT validated by backend via /auth/v1/user)
          ── Storage (silhouette images)
```

```
/backend
├── server.py            # FastAPI entry, /api router, CORS, /health
├── db.py                # asyncpg pool → Supabase (statement_cache_size=0)
├── auth.py              # get_current_user (validates Supabase JWT) + get_user_or_guest
├── models.py, utils.py
├── data/buildings.py    # 60 buildings w/ Supabase Storage silhouette URLs
├── routes/              # auth, buildings, puzzle, stats, friends, leaderboard, achievements, challenges
├── Procfile             # Railway start command
├── railway.json         # Railway build/start/healthcheck config
└── runtime.txt          # Python 3.11.15

/frontend
├── src/lib/api.js       # axios; attaches Supabase JWT or guest id to every request
├── src/lib/supabase.js  # Supabase client init
├── src/contexts/        # AuthContext (Supabase session), ThemeContext
├── src/pages/           # DailyPuzzle, Login, Profile, Leaderboard, History, Challenges
├── src/components/       # Navbar, ProtectedRoute, ui/ (shadcn)
└── vercel.json          # CRA build + SPA rewrites
```

---

## 4. Features Implemented

- **Daily puzzle** — 114 famous buildings, silhouette from Supabase Storage, 6-guess limit, auto-selected by date.
- **Hints** — direction arrow + distance (km) on each wrong guess (Haversine formula); silhouette reveal on solve.
- **Auth** — Google OAuth + email/password via Supabase; full **guest mode** with localStorage stats.
- **Profile & stats** — puzzles played/solved, current & longest streak, win rate, perfect solves.
- **Friends** — search, request/accept/decline, remove; friends leaderboard.
- **Leaderboards** — overall + friends, by streak / wins / win-rate.
- **Achievements** — badge set unlocked by milestones.
- **Challenges** — weekly/monthly challenges with their own leaderboards.
- **Past puzzles / history** — archive of previous days (signed-in).
- **Share** — Wordle-style emoji result string.
- **UX** — mobile-responsive, light/dark theme, catch-all route → home.

---

## 5. Data Model (PostgreSQL)

| Table | Key fields |
|---|---|
| `users` | `user_id`, `supabase_uid`, `email`, `username`, `name`, `picture`, `join_date` |
| `buildings` | `building_id`, `name`, `aliases`, `latitude`, `longitude`, `silhouette_url`, `city`, `country` |
| `daily_puzzles` | `id`, `puzzle_date`, `building_id` |
| `guesses` | `id`, `user_id`, `puzzle_date`, `guess_building_id`, `is_correct`, `direction`, `distance_km` |
| `friendships` | `id`, `user_id`, `friend_id`, `status` |
| `user_stats` | `user_id`, `puzzles_played`, `puzzles_solved`, `current_streak`, `longest_streak` |

### 5.1 Security model — RLS posture (do not change without reading this)

All database access goes through the FastAPI backend, which authorizes every request at
the application layer (`get_current_user` / `get_user_or_guest` in `auth.py`). The backend
connects using the **direct Postgres connection string** (`SUPABASE_DB_URL`, the `postgres`
role), which **bypasses RLS** and does not depend on `anon`/`authenticated` grants.

Clients use Supabase **only for authentication** (to obtain a JWT). The frontend never calls
the Supabase Data API (PostgREST) to read or write tables. The public `anon` key shipped in
the frontend bundle must therefore have **zero** data access.

The enforced posture on every table (`users`, `guesses`, `user_stats`, `friendships`,
`achievement_notifications`, `buildings`) is:

- **RLS enabled**, with **no policies** for `anon`/`authenticated` (RLS with no policy denies all rows).
- **All privileges revoked** from `anon` and `authenticated` (defense in depth).

> ⚠️ **Do not add permissive policies** (`USING (true)` / `WITH CHECK (true)`). They would
> re-expose every table to anyone holding the public anon key, bypassing the backend
> entirely. The Supabase Security Advisor flags these as "RLS Policy Always True." If you
> ever need client-direct table access, design real per-row policies — `user_id` is a custom
> string (`user_xxxx`), not `auth.uid()`; the auth UID maps to `users.supabase_uid`.

Verify the posture anytime with:

```sql
select c.relname as "table", c.relrowsecurity as rls_enabled,
  (select count(*) from pg_policies p where p.schemaname='public' and p.tablename=c.relname) as policy_count,
  coalesce(string_agg(distinct g.privilege_type, ', '), '(none)') as anon_auth_privs
from pg_class c join pg_namespace n on n.oid=c.relnamespace
left join information_schema.role_table_grants g
  on g.table_schema='public' and g.table_name=c.relname and g.grantee in ('anon','authenticated')
where n.nspname='public'
  and c.relname in ('users','guesses','user_stats','friendships','achievement_notifications','buildings')
group by c.relname, c.relrowsecurity order by c.relname;
-- Expect every row: rls_enabled=true, policy_count=0, anon_auth_privs=(none)
```

---

## 6. Key API Endpoints (prefix `/api`)

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | Creates/returns app user from a Supabase JWT |
| GET | `/auth/me` | Current user |
| PUT | `/auth/profile` | Update username |
| GET | `/puzzle/today` | Today's puzzle (guest or authed) |
| POST | `/puzzle/guess` | Submit a guess → hint / solve |
| GET | `/puzzle/calendar`, `/puzzle/past/{date}`, `/puzzle/share` | Archive & share |
| GET | `/buildings`, `/buildings/search?q=` | Building list & search |
| GET | `/stats/me` | User stats |
| GET | `/leaderboard/overall?metric=`, `/leaderboard/friends` | Leaderboards |
| GET/POST/DELETE | `/friends/*` | Friend system |
| GET | `/achievements/me`, `/challenges/current`, `/challenges/leaderboard` | Achievements & challenges |
| GET | `/health` (root, no `/api`) | Health check for Railway |

**Auth model:** Frontend sends `Authorization: Bearer <supabase_jwt>`; backend validates by calling
Supabase `/auth/v1/user`. No token → falls back to `X-Guest-ID` for guest play. Invalid token → 401.

---

## 7. Deployment & Configuration

**Backend (Railway):** root dir `backend`; start `uvicorn server:app --host 0.0.0.0 --port $PORT`; healthcheck `/health`.

Required env vars (Railway):
```
SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET, SUPABASE_DB_URL,
CORS_ORIGINS   # set to https://www.silhouettele.cc,https://silhouettele.cc
```

**Frontend (Vercel):** root dir `frontend`; build `yarn build`; output `build`; SPA rewrites via `vercel.json`.

Required env vars (Vercel):
```
REACT_APP_BACKEND_URL=https://api.silhouettele.cc
REACT_APP_SUPABASE_URL=https://<project>.supabase.co
REACT_APP_SUPABASE_ANON_KEY=<anon key>
```

**Supabase Auth → URL Configuration:** Site URL `https://www.silhouettele.cc`; Redirect URLs include `https://www.silhouettele.cc/**`.

**DNS (Namecheap):** apex `silhouettele.cc` → Vercel A record; `www` → `cname.vercel-dns.com`; `api` → Railway CNAME.

> See `DEPLOYMENT.md` for the full step-by-step guide.

---

## 8. Status

- ✅ Live on custom domain `silhouettele.cc`.
- ✅ Bearing model = **rhumb-line ("compass")** so directions match flat-map intuition (Paris→KL reads SE, not E). Distances are great-circle (accurate). Locked by `backend/tests/test_directions.py`.
- ✅ Direction indicators use **consistent emoji** (forced emoji presentation via U+FE0F) across all guesses + 🎯 for the correct answer; derived on the frontend from the stored compass code (no DB migration).
- ✅ Backend regression: **58/58 tests pass** (guest + authenticated flows, hints, correct-guess solve, leaderboards, friends, achievements, challenges, directions).
- ⚠️ Pre-existing lint false-positive (`react-hooks/set-state-in-effect` on the dropdown effect in DailyPuzzlePage.js) — not introduced here, present in git HEAD; production build compiles fine.
- ⚠️ Final Google-button login click must be verified manually (cannot be automated).

---

## 9. Suggested Next Steps

**P1 — Monetization (Stripe "Silhouettele Premium")**
- Monthly subscription; gate the **Past Puzzles archive** as the first premium perk.
- One-time purchases (e.g. extra guesses, hint reveals).

**P1 — Auth polish**
- Brand the Google consent screen (App name + logo; publish to Production) so it reads "Silhouettele" instead of the Supabase project URL. (Optional: Supabase Custom Domain for `auth.silhouettele.cc`.)
- Add `https://silhouettele.cc` to `CORS_ORIGINS` alongside the `www` host.

**P2 — Engagement & retention**
- "Send a hint to a friend" / challenge a friend on today's puzzle.
- Daily streak reminders (email via Resend, or web push).
- Result-sharing with an image card (Open Graph) for social virality.

**P3 — Platform**
- PWA (installable on mobile, offline daily puzzle cache).
- Analytics (e.g. Plausible/PostHog) for funnel + retention.
- Admin tooling to curate/schedule daily puzzles and add new buildings.

**Nice-to-haves**
- Local JWT verification with `SUPABASE_JWT_SECRET` to remove the per-request call to Supabase `/auth/v1/user` (lower latency).
- Remove stale `MONGO_URL` / `DB_NAME` from backend env (unused post-migration).
