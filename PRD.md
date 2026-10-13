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
| Storage | Supabase Storage — 114 silhouette PNGs in public `silhouettes` bucket (one per building) |
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

## 9. Development Roadmap & Priorities

> **Revised June 2026** after a structured priority review (LLM Council, 5 perspectives + peer
> review). The earlier ordering led with **monetization**; that was judged backwards by every
> perspective. The corrected thesis is **measure → secure content & freshness → retention &
> first-run UX → *then* monetize**. Rationale and the demoted items are kept below so the
> reasoning survives, not just the conclusion.

### Guiding principle

Silhouettele is a **daily-habit** game; its only core promise is *"come back tomorrow — there's a
fresh one."* Every candidate is judged against two questions: **(1)** does it protect the daily
habit, and **(2)** can we tell whether it worked? Today we cannot answer (2) at all — there is
**no analytics** — which makes every other call a guess. That gates the whole roadmap.

### Current reality check (verified against code, June 2026)

- **Shipped:** daily puzzle, guest mode, Google + email auth, friends, daily/all-time/friends
  leaderboards, achievements, weekly/monthly challenges (each with its own leaderboard),
  past-puzzles archive, Wordle-style share strings, **server-rendered Open Graph cards**
  (`backend/routes/og.py`), player-facing changelog (`/changelog`), light/dark themes, mobile
  responsive. *(Note: OG cards, previously listed here as future P2, are already live. A
  head-to-head "challenge a friend" is **not** built: `routes/challenges.py` serves only the
  weekly/monthly challenges and their leaderboard.)*
- **Content:** **114 buildings, all 114 with silhouettes** (`backend/data/buildings.py`;
  verified `len(BUILDINGS) == len(SILHOUETTE_URLS) == 114`, zero gaps). ≈ **3.7 months** of
  distinct inventory at one puzzle/day. *(Supersedes the old "60 silhouette PNGs" figure.)*
- **Selection is a stateless hash, not a schedule:** `get_daily_building_id` =
  `md5("silhouettele-"+date) % len(BUILDINGS)` (`backend/utils.py:42`). It picks **with
  replacement and no de-duplication**, so the same building recurs by random collision within
  **~2 weeks** (birthday paradox) while ~100 others stay unseen. The `daily_puzzles` table exists
  in the schema (§5) but is **unused** by the puzzle route (`routes/puzzle.py` calls the hash
  directly) — a ready-made hook for real scheduling.
- **Not built:** any **analytics** (no PostHog/Plausible/GA — zero data on DAU, retention,
  funnel); any **monetization** (no payment code or routes exist); head-to-head challenges;
  streak reminders; PWA; admin/content tooling.

### Phase 0 — Instrument (this week, ~½–1 day) — do this first

Without usage data, every item below — including this roadmap — is unfalsifiable.
- Add **privacy-friendly analytics**. **Plausible** preferred (cookieless → sidesteps most
  GDPR/cookie-consent overhead); **PostHog** if you want funnels and session insight.
- Instrument the core funnel: visit → puzzle started → guess submitted → solved/failed →
  share clicked → guest → sign-up.
- **Define the monetization decision-gate now**, as a trigger not a vibe — e.g. *"open Stripe
  work only once we sustain ≥ N DAU at ≥ X% D7 retention."* Fill in N / X after the first week
  of data lands.

### Phase 1 — Protect content & freshness (1–2 weeks) — the existential one

A daily game that silently repeats trains its most engaged players (the ones who notice first)
to leave. Two distinct problems: **random repeats now**, and **finite runway soon**.
- **Switch selection to a real schedule.** Populate and read the existing `daily_puzzles` table
  so each date maps to a curated, **non-repeating** building until the pool is exhausted; retire
  the stateless hash for live selection. This kills the "repeat within 2 weeks" bug and gives
  control over ordering (and themed weeks later).
- **Build a content-loading script** (a small CLI, **not** a full admin UI — that's the
  multi-week time-sink; defer it). Input an image + `name / aliases / lat / lng / city /
  country / year_built / height_m / fun_fact`; it uploads the PNG to Supabase Storage and
  appends the record. ⚠️ The hint engine needs **lat/lng per building**, so "just drop a PNG" is
  insufficient — the metadata is the real work.
- **Extend the runway** toward 6–12 months by bulk-adding buildings. Watch two risks:
  **image/silhouette licensing** (sourcing imagery at scale) and **silhouette quality**
  (ambiguous/unfair silhouettes wreck the first-run experience).
- *Stop-gap if pressed:* with proper scheduling, controlled reuse on a long cycle is acceptable
  (Wordle reuses answers) — the bug today is **random** repeats, not reuse per se.

### Phase 2 — Retention & first-run clarity (weeks 3–4)

Acquisition is wasted if first-time players bounce or solvers don't return.
- **Nail the new-player "aha" in ~5 seconds.** Make the rules instantly legible: what the
  direction/distance refers to (the building's real-world location) and what counts as a correct
  answer (building name vs city).
- **Guarantee a satisfying reveal on a loss** (show the building + its `fun_fact`) so failing
  still rewards a return visit.
- **One retention hook:** streak-reminder email via **Resend** — but build it *after* analytics
  confirm people return, so you're amplifying a real curve, not an imagined one.

### Phase 3 — Monetize from leverage (month 2–3, only if the gate is met)

- Build Stripe **only once Phase 0 data proves a returning audience** worth charging.
- **Do not gate the past-puzzles archive.** It is the buffer against the content shortage, so
  paywalling it accelerates churn at the worst possible moment ("taxing the exit").
- Prefer monetizing **strength, not the exit**: cosmetics/themes, a supporter/tip tier, gifting,
  or **sponsored themed weeks** (e.g. a tourism board sponsoring a "Wonders of the World" week).
- **Brand the Google consent screen here** (so it reads "Silhouettele", not the Supabase URL;
  publish to Production). This polish matters most at the moment you ask for money — it was
  previously mis-prioritised as a standalone P1.

### Back-pocket upside (don't chase yet)

The silhouette + compass-triangulation loop **generalises** beyond buildings (flags, landmarks,
logos, skylines) — a genuine franchise option. But peer review flagged expanding verticals
before proving day-2 retention as **premature scaling**. The cheap, on-brand version is **themed
weeks using the buildings you already have**, unlocked for free by Phase 1's scheduler.

### Still-valid engineering hygiene (low priority, do opportunistically)

- Local JWT verification with `SUPABASE_JWT_SECRET` to drop the per-request call to Supabase
  `/auth/v1/user` (lower latency).
- Remove stale `MONGO_URL` / `DB_NAME` env vars from the backend (unused post-migration).
- Add `https://silhouettele.cc` to `CORS_ORIGINS` alongside the `www` host.

### Sequence at a glance

| # | Phase | Effort | Gate |
|---|---|---|---|
| 0 | Analytics + decision-gate | ½–1 day | — (do now) |
| 1 | Scheduled non-repeating selection + content loader + more buildings | 1–2 wks | — (existential) |
| 2 | First-run clarity + loss reveal + streak email | 1–2 wks | streak email waits on Phase 0 retention data |
| 3 | Stripe — cosmetics/supporter/sponsorship, **not** archive-gating | 1–2 wks | only once DAU/retention gate is met |

> **Why monetization moved last:** you cannot price a subscription for an audience you can't
> measure, the obvious first perk (the archive) is exactly the wrong thing to gate, and the daily
> habit must be protected before it's worth charging for. Revenue is captured *from* a habit —
> build the habit's foundations first.
