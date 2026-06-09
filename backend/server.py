from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from db import init_db, close_db, get_pool
from data.buildings import BUILDINGS, SILHOUETTE_URLS
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
from routes.og import router as og_router

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


async def _seed_buildings_if_empty():
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM buildings")
    if count > 0:
        logger.info("Buildings already seeded (%d rows), skipping.", count)
        return
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
    logger.info("Seeded %d buildings.", len(BUILDINGS))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _seed_buildings_if_empty()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(buildings_router)
api_router.include_router(puzzle_router)
api_router.include_router(stats_router)
api_router.include_router(friends_router)
api_router.include_router(leaderboard_router)
api_router.include_router(achievements_router)
api_router.include_router(challenges_router)
api_router.include_router(og_router)

app.include_router(api_router)

_cors_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',') if o.strip()]
if not _cors_origins:
    raise RuntimeError("CORS_ORIGINS environment variable must be set to a comma-separated list of allowed origins")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
