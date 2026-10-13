"""Server-rendered Open Graph image for today's puzzle.

Returns a branded 1200x630 PNG so links to silhouettele.cc auto-preview with an
attractive, daily-refreshing card in Twitter/Discord/Slack/iMessage etc.
"""
import asyncio
import io
from functools import lru_cache

import httpx
from fastapi import APIRouter, Response
from PIL import Image, ImageDraw, ImageFont

from utils import get_daily_building_id, get_today_str, get_building_by_id
from data.buildings import SILHOUETTE_URLS

router = APIRouter(prefix="/og", tags=["og"])

# System fonts are tried in order. Railway's build image ships none of them,
# so the last resort is Pillow's bundled font, which always exists.
_FONT_CANDIDATES = {
    True: [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    False: [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}
_INDIGO = (99, 102, 241)
_MUTED = (154, 160, 181)
_WIDTH, _HEIGHT = 1200, 630

# In-memory cache: today's PNG bytes, keyed by date (renders at most once/day).
_CACHE: dict[str, bytes] = {}
_RENDER_LOCK = asyncio.Lock()


@lru_cache(maxsize=None)
def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _gradient(top: tuple, bottom: tuple) -> Image.Image:
    base = Image.new("RGB", (_WIDTH, _HEIGHT), top)
    draw = ImageDraw.Draw(base)
    for y in range(_HEIGHT):
        t = y / _HEIGHT
        draw.line(
            [(0, y), (_WIDTH, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )
    return base


def _tracked(draw: ImageDraw.ImageDraw, pos: tuple, text: str, font, fill, spacing: int = 0) -> None:
    x, y = pos
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def _render(date_str: str, building: dict | None, sil_bytes: bytes | None) -> bytes:
    img = _gradient((20, 20, 43), (11, 11, 20))
    draw = ImageDraw.Draw(img)

    # Brand
    draw.rounded_rectangle([70, 70, 126, 126], radius=14, fill=_INDIGO)
    draw.text((86, 76), "S", font=_font(46), fill=(255, 255, 255))
    draw.text((146, 74), "Silhouettele", font=_font(42), fill=(255, 255, 255))
    _tracked(draw, (149, 124), "LOOPSTONE GAMES", _font(18), _MUTED, spacing=6)

    # Headline
    draw.text((70, 248), "Guess the building", font=_font(58), fill=(255, 255, 255))
    draw.text((70, 320), "from its silhouette", font=_font(58), fill=(255, 255, 255))

    # Date + subtitle
    draw.text((70, 432), date_str, font=_font(30), fill=_INDIGO)
    draw.text((70, 476), "A new puzzle every day  -  6 guesses", font=_font(28, bold=False), fill=_MUTED)

    # Footer
    _tracked(draw, (70, 548), "SILHOUETTELE.CC", _font(22), _MUTED, spacing=4)

    # White panel + silhouette
    px0, py0, side = 760, 125, 380
    draw.rounded_rectangle([px0, py0, px0 + side, py0 + side], radius=28, fill=(255, 255, 255))
    if sil_bytes:
        try:
            sil = Image.open(io.BytesIO(sil_bytes)).convert("RGBA")
            pad = 46
            sil.thumbnail((side - 2 * pad, side - 2 * pad), Image.LANCZOS)
            ox = px0 + (side - sil.width) // 2
            oy = py0 + (side - sil.height) // 2
            img.paste(sil, (ox, oy), sil)
        except Exception:
            pass

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@router.get("/today.png")
async def og_today():
    date_str = get_today_str()
    if date_str in _CACHE:
        return Response(content=_CACHE[date_str], media_type="image/png",
                        headers={"Cache-Control": "public, max-age=3600"})

    async with _RENDER_LOCK:
        if date_str in _CACHE:
            return Response(content=_CACHE[date_str], media_type="image/png",
                            headers={"Cache-Control": "public, max-age=3600"})

        bid = get_daily_building_id(date_str)
        building = get_building_by_id(bid)
        url = SILHOUETTE_URLS.get(bid)
        sil_bytes = None
        if url:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    sil_bytes = resp.content
            except Exception:
                sil_bytes = None
        rendered = _render(date_str, building, sil_bytes)
        _CACHE.clear()
        _CACHE[date_str] = rendered

    return Response(content=_CACHE[date_str], media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"})
