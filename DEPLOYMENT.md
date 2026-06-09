# Silhouettele — Railway (Backend) + Vercel (Frontend) Deployment Guide

This app is split into two deployables:
- **Backend** (`/backend`) → **Railway** (FastAPI + asyncpg → Supabase Postgres)
- **Frontend** (`/frontend`) → **Vercel** (React / CRA + CRACO)

Supabase (DB, Auth, Storage) is already hosted — you do **not** deploy it.

---

## Prerequisites
- Code pushed to a GitHub repo (use the **"Save to GitHub"** button in the Emergent chat).
- Railway account + Vercel account (you have both).
- Your Supabase keys handy (already in `backend/.env` and `frontend/.env`).

---

## STEP 1 — Deploy the Backend to Railway

1. Railway → **New Project** → **Deploy from GitHub repo** → select your repo.
2. Open the service → **Settings**:
   - **Root Directory**: `backend`
   - Railway auto-detects Python (Nixpacks). The included `Procfile` / `railway.json` sets the start command:
     `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Healthcheck path** is preset to `/health`.
3. **Variables** tab → add these (copy values from your `backend/.env`):
   ```
   SUPABASE_URL          = https://urpkmgxvshdlkiaucykf.supabase.co
   SUPABASE_ANON_KEY     = <your anon key>
   SUPABASE_JWT_SECRET   = <your jwt secret>
   SUPABASE_DB_URL       = <your full postgres connection string with password>
   CORS_ORIGINS          = https://<your-vercel-domain>.vercel.app
   ```
   - ⚠️ Do **not** add `MONGO_URL` / `DB_NAME` — no longer used.
   - You can set `CORS_ORIGINS` to a temporary `*` first, then tighten it to the Vercel URL after Step 2.
   - For `SUPABASE_DB_URL`, use the **pooled** connection string (port `6543`, host `...pooler.supabase.com`). The code already sets `statement_cache_size=0` for pgbouncer compatibility.
4. **Deploy**. Once live, Railway gives you a public URL, e.g. `https://silhouettele-backend.up.railway.app`.
5. Verify:
   ```
   curl https://<your-railway-url>/health           # {"status":"ok"}
   curl https://<your-railway-url>/api/buildings     # list of buildings
   ```

---

## STEP 2 — Deploy the Frontend to Vercel

1. Vercel → **Add New… → Project** → import the same GitHub repo.
2. **Configure Project**:
   - **Root Directory**: `frontend`
   - Framework Preset: **Create React App** (auto-detected; `vercel.json` pins build = `yarn build`, output = `build`, plus SPA rewrites for React Router).
3. **Environment Variables** (copy from `frontend/.env`, but point the backend URL at Railway):
   ```
   REACT_APP_BACKEND_URL       = https://<your-railway-url>     # NO trailing slash, NO /api
   REACT_APP_SUPABASE_URL      = https://urpkmgxvshdlkiaucykf.supabase.co
   REACT_APP_SUPABASE_ANON_KEY = <your anon key>
   ```
4. **Deploy**. You'll get e.g. `https://silhouettele.vercel.app`.

---

## STEP 3 — Wire the two together (CORS + OAuth redirects)

1. **CORS**: Back in Railway → Variables, set
   `CORS_ORIGINS = https://<your-vercel-domain>.vercel.app` → redeploy.
2. **Supabase Auth redirect URLs** (Supabase Dashboard → Authentication → URL Configuration):
   - **Site URL**: `https://<your-vercel-domain>.vercel.app`
   - **Redirect URLs**: add `https://<your-vercel-domain>.vercel.app/**`
3. **Google OAuth** (Google Cloud Console → Credentials → your OAuth client):
   - Authorized redirect URI must include Supabase's callback:
     `https://urpkmgxvshdlkiaucykf.supabase.co/auth/v1/callback`
   - (This is unchanged by hosting — it points at Supabase, not Vercel.)

---

## STEP 4 — Smoke test production
- Open the Vercel URL → guest play loads today's puzzle.
- Sign in with Google → you should land back on the app, logged in.
- Submit a guess → directional/distance hint shows.
- Check Profile / Leaderboards load.

---

## Notes
- `load_dotenv()` in the backend is harmless in production — when no `.env` file exists, values are read straight from Railway env vars.
- Frontend production builds **exclude** the Emergent visual-edits and health-check tooling (they only load in dev), so the Vercel bundle is clean.
- Free Railway/Supabase tiers may pause on inactivity; the first request after idle can be slow.
