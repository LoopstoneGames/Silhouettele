import re
import unicodedata
from difflib import SequenceMatcher

from fastapi import APIRouter

from data.buildings import BUILDINGS

router = APIRouter(prefix="/buildings", tags=["buildings"])

# Ligatures NFKD does not decompose on its own.
_LIGATURES = {"œ": "oe", "æ": "ae", "ø": "o", "ß": "ss", "ð": "d", "þ": "th", "ł": "l"}


def _norm(s: str) -> str:
    """Lowercase, strip accents/ligatures/punctuation -> plain ascii words."""
    s = (s or "").lower()
    for k, v in _LIGATURES.items():
        s = s.replace(k, v)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def _searchable(b):
    aliases = [a for a in (b.get("aliases", "") or "").replace(";", ",").split(",") if a.strip()]
    return {
        "names": [_norm(b["name"])] + [_norm(a) for a in aliases],
        "places": [_norm(b["city"]), _norm(b["country"])],
    }


# Pre-normalize search fields once at import (114 buildings -> cheap).
_INDEX = {b["building_id"]: _searchable(b) for b in BUILDINGS}


def _field_score(field: str, nq: str) -> float:
    if not field:
        return 0.0
    if field == nq:
        return 1.0
    if field.startswith(nq):
        return 0.95
    if nq in field:
        return 0.86
    best = SequenceMatcher(None, nq, field).ratio()
    for tok in field.split():
        if len(nq) >= 3 and tok.startswith(nq):
            best = max(best, 0.9)
        best = max(best, SequenceMatcher(None, nq, tok).ratio())
    return best


def _score(building_id: str, nq: str) -> float:
    idx = _INDEX[building_id]
    s = 0.0
    for f in idx["names"]:
        s = max(s, _field_score(f, nq))
    for f in idx["places"]:
        s = max(s, _field_score(f, nq) * 0.7)  # city/country weighted below names
    return s


@router.get("/search")
async def search_buildings(q: str = ""):
    nq = _norm(q)
    if len(nq) < 2:
        return []
    # Short queries: require a real (sub)string hit to avoid fuzzy noise.
    threshold = 0.86 if len(nq) <= 3 else 0.62
    scored = []
    for b in BUILDINGS:
        sc = _score(b["building_id"], nq)
        if sc >= threshold:
            scored.append((sc, b))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [
        {"building_id": b["building_id"], "name": b["name"], "city": b["city"], "country": b["country"]}
        for _, b in scored[:10]
    ]


@router.get("")
async def list_buildings():
    return [
        {"building_id": b["building_id"], "name": b["name"], "city": b["city"], "country": b["country"]}
        for b in BUILDINGS
    ]
